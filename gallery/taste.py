import math
import re

from django.db.models import F, Q, Count

from .models import (
    Agent,
    Interaction,
    Match,
    Nationality,
    TasteSignal,
)

ALPHA = 2                   # Bayesian smoothing parameter
MATCH_CHECK_INTERVAL = 15   # Number of swipes between match checks for a user
MATCH_THRESHOLD = 0.3       # Minimum cosine similarity to consider a match
MIN_EVIDENCE = 3            # Minimum total swipes for a facet value to be included in taste vector
COLD_START_THRESHOLD = 20   # Minimum swipes for a user to be included in matching pool


def parse_century(date_str):
    """Extract a century number from a date string like 'ca. 1720-25' -> 18."""
    if not date_str:
        return None
    match = re.search(r"\b(\d{4})\b", date_str)
    if match:
        year = int(match.group(1))
        return year // 100 + 1
    return None


def bayesian_score(likes, passes):
    """Compute smoothed Bayesian score: (likes + alpha) / (likes + passes + 2 * alpha)."""
    return (likes + ALPHA) / (likes + passes + 2 * ALPHA)


def get_artwork_facet_values(artwork):
    """
    Return a list of (facet, value) tuples for an artwork,
    traversing its classifiers, departments, nationalities, and century.
    """
    facets = []

    # Classifiers
    for cls in artwork.classifiers.all():
        facets.append(("classifier", cls.name))

    # Departments
    for dept in artwork.departments.all():
        facets.append(("department", dept.name))

    # Nationalities (from productions -> agents -> nationalities)
    agent_ids = list(
        artwork.agents.values_list("id", flat=True)
    )
    if agent_ids:
        nat_descriptors = (
            Nationality.objects
            .filter(agentnationality__agent_id__in=agent_ids)
            .values_list("descriptor", flat=True)
            .distinct()
        )
        for nat in nat_descriptors:
            facets.append(("nationality", nat))

    # Century (try to parse from object date, fallback to agent birth date)
    century = parse_century(artwork.date)
    if century is None and agent_ids:
        agent_dates = (
            Agent.objects
            .filter(id__in=agent_ids, begin_date__isnull=False)
            .values_list("begin_date", flat=True)[:1]
        )
        for d in agent_dates:
            century = d.year // 100 + 1
    if century is not None:
        facets.append(("century", str(century)))

    return facets


def update_taste_signals(user, artwork, action, undo=False):
    """
    Increment (or decrement if undo) the taste signal counters
    for all facet values associated with an artwork.
    """
    facet_values = get_artwork_facet_values(artwork)
    delta = -1 if undo else 1

    for facet, value in facet_values:
        signal, _ = TasteSignal.objects.get_or_create(
            user=user, facet=facet, value=value,
            defaults={"like_count": 0, "pass_count": 0, "score": 0.5},
        )

        if action == "like":
            signal.like_count = max(0, signal.like_count + delta)
        else:
            signal.pass_count = max(0, signal.pass_count + delta)

        signal.score = bayesian_score(signal.like_count, signal.pass_count)
        signal.save()


def check_matches(user):
    """
    Compare the current user's taste vector against all eligible
    candidates and insert Match rows for pairs above the threshold.
    """
    # Load user's taste vector, filtered by minimum evidence
    my_signals = (
        TasteSignal.objects
        .filter(user=user)
        .annotate(total=F("like_count") + F("pass_count"))
        .filter(total__gte=MIN_EVIDENCE)
    )
    my_vector = {(s.facet, s.value): s.score for s in my_signals}
    if not my_vector:
        return

    # Find users already matched with me (to exclude)
    already_matched_qs = Match.objects.filter(
        Q(user1=user) | Q(user2=user)
    ).values_list("user1_id", "user2_id")

    matched_ids = set()
    for u1, u2 in already_matched_qs:
        matched_ids.add(u1)
        matched_ids.add(u2)
    matched_ids.discard(user.id)

    # Find candidate user IDs: share at least one (facet, value),
    # not already matched, and above cold-start threshold
    facet_q = Q()
    for facet, value in my_vector:
        facet_q |= Q(facet=facet, value=value)

    candidate_ids = (
        TasteSignal.objects
        .filter(facet_q)
        .exclude(user=user)
        .exclude(user_id__in=matched_ids)
        .values_list("user_id", flat=True)
        .distinct()
    )

    # Filter to users above cold-start threshold
    candidate_ids = list(
        Interaction.objects
        .filter(user_id__in=candidate_ids)
        .values("user_id")
        .annotate(swipe_count=Count("id"))
        .filter(swipe_count__gte=COLD_START_THRESHOLD)
        .values_list("user_id", flat=True)
    )
    if not candidate_ids:
        return

    # Batch-load candidate vectors (single query)
    candidate_signals = (
        TasteSignal.objects
        .filter(user_id__in=candidate_ids)
        .annotate(total=F("like_count") + F("pass_count"))
        .filter(total__gte=MIN_EVIDENCE)
    )

    candidate_vectors = {}
    for s in candidate_signals:
        if s.user_id not in candidate_vectors:
            candidate_vectors[s.user_id] = {}
        candidate_vectors[s.user_id][(s.facet, s.value)] = s.score

    # Compute cosine similarity and collect new matches
    my_norm = math.sqrt(sum(v ** 2 for v in my_vector.values()))
    if my_norm == 0:
        return

    new_matches = []
    for cand_id, cand_vector in candidate_vectors.items():
        dot = sum(
            my_vector.get(k, 0) * v for k, v in cand_vector.items()
        )
        cand_norm = math.sqrt(sum(v ** 2 for v in cand_vector.values()))
        if cand_norm == 0:
            continue

        similarity = dot / (my_norm * cand_norm)

        if similarity >= MATCH_THRESHOLD:
            u1, u2 = sorted([user.id, cand_id])
            new_matches.append(
                Match(user1_id=u1, user2_id=u2, similarity=similarity)
            )

    if new_matches:
        Match.objects.bulk_create(new_matches, ignore_conflicts=True)
