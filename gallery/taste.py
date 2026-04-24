import hashlib
import math
import re
from collections import defaultdict
from datetime import date

from django.db.models import F, Q, Count, Sum, Case, When, Value, FloatField

from .models import (
    Agent,
    Artwork,
    Interaction,
    Match,
    Nationality,
    ObjectClassifier,
    ObjectDepartment,
    Production,
    TasteSignal,
)

ALPHA = 2                   # Bayesian smoothing parameter
MATCH_CHECK_INTERVAL = 15   # Number of swipes between match checks for a user
MATCH_THRESHOLD = 0.3       # Minimum cosine similarity to consider a match
MIN_EVIDENCE = 3            # Minimum total swipes for a facet value to be included in taste vector
COLD_START_THRESHOLD = 20   # Minimum swipes for a user to be included in matching pool
DAILY_CANDIDATES = 10       # Number of art-of-the-day candidates to return


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


def get_daily_artwork(user):
    """
    Return a list of top-scoring artwork IDs for this user today,
    plus an explanation of which taste facets drove the pick.

    Cold-start users (< COLD_START_THRESHOLD interactions) get the
    globally most-liked artworks instead.
    """
    total_interactions = Interaction.objects.filter(user=user).count()

    if total_interactions < COLD_START_THRESHOLD:
        return _daily_cold_start(user), []

    # Only include signals with enough evidence
    signals = list(
        TasteSignal.objects
        .filter(user=user)
        .annotate(total=F("like_count") + F("pass_count"))
        .filter(total__gte=MIN_EVIDENCE)
    )
    if not signals:
        return _daily_cold_start(user), []

    signal_map = {(s.facet, s.value): s.score for s in signals}

    # Subquery for excluding artworks the user has already seen
    seen_subquery = (
        Interaction.objects
        .filter(user=user)
        .values("artwork_id")
    )

    scores = defaultdict(float)

    # Score each facet type using DB-side aggregation via Case/When,
    # so only (artwork_id, score) pairs come back — not raw rows.
    _score_facet(
        scores, signal_map, "classifier",
        ObjectClassifier.objects
        .filter(classifier__name__in=_facet_values(signal_map, "classifier"))
        .exclude(artwork_id__in=seen_subquery),
        artwork_field="artwork_id",
        value_lookup="classifier__name",
    )

    _score_facet(
        scores, signal_map, "department",
        ObjectDepartment.objects
        .filter(department__name__in=_facet_values(signal_map, "department"))
        .exclude(artwork_id__in=seen_subquery),
        artwork_field="artwork_id",
        value_lookup="department__name",
    )

    _score_facet(
        scores, signal_map, "nationality",
        Production.objects
        .filter(agent__nationalities__descriptor__in=_facet_values(signal_map, "nationality"))
        .exclude(artwork_id__in=seen_subquery),
        artwork_field="artwork_id",
        value_lookup="agent__nationalities__descriptor",
        distinct=True,
    )

    # Century — only boost artworks already scored by other facets,
    # since parsing date strings across 182k rows would be wasteful.
    century_values = {v for (f, v) in signal_map if f == "century"}
    if century_values and scores:
        for artwork in (
            Artwork.objects
            .filter(id__in=scores.keys())
            .exclude(date__isnull=True)
            .only("id", "date")
        ):
            century = parse_century(artwork.date)
            if century and str(century) in century_values:
                scores[artwork.id] += signal_map[("century", str(century))]

    if not scores:
        return _daily_cold_start(user), []

    # Deterministic daily tiebreaker so the same user sees the same pick all day
    today = date.today().isoformat()

    def daily_sort_key(item):
        aid, score = item
        tiebreak = hashlib.md5(f"{aid}{today}".encode()).hexdigest()
        return (-score, tiebreak)

    ranked = sorted(scores.items(), key=daily_sort_key)[:DAILY_CANDIDATES]
    artwork_ids = [aid for aid, _ in ranked]

    # Build explanation from the top-scoring artwork
    top_artwork = Artwork.objects.get(id=artwork_ids[0])
    explanation = _build_explanation(signal_map, top_artwork)

    return artwork_ids, explanation


def _facet_values(signal_map, facet):
    """Extract the value list for a given facet from the signal map."""
    return [v for (f, v) in signal_map if f == facet]


def _score_facet(scores, signal_map, facet, queryset, artwork_field, value_lookup, distinct=False):
    """
    Aggregate artwork scores for a single facet type in the database.

    Builds a Case/When expression mapping each facet value to its taste score,
    then SUMs per artwork — so only (artwork_id, total_score) rows are returned.
    """
    values = _facet_values(signal_map, facet)
    if not values:
        return

    score_expr = Case(
        *[
            When(**{value_lookup: v, "then": Value(signal_map[(facet, v)])})
            for v in values
        ],
        output_field=FloatField(),
    )

    qs = queryset.values(artwork_field)
    if distinct:
        qs = qs.distinct()
    rows = qs.annotate(facet_score=Sum(score_expr)).values_list(artwork_field, "facet_score")

    for aid, facet_score in rows:
        if facet_score:
            scores[aid] += facet_score


def _daily_cold_start(user):
    """Return the most globally liked artwork IDs for cold-start users."""
    seen_subquery = (
        Interaction.objects
        .filter(user=user)
        .values("artwork_id")
    )
    popular = (
        Interaction.objects
        .filter(action="like")
        .exclude(artwork_id__in=seen_subquery)
        .values("artwork_id")
        .annotate(like_count=Count("id"))
        .order_by("-like_count")[:DAILY_CANDIDATES]
    )
    return [row["artwork_id"] for row in popular]


def _build_explanation(signal_map, artwork):
    """
    Intersect an artwork's facet values with the user's taste signals
    to explain why this artwork was recommended.
    """
    artwork_facets = get_artwork_facet_values(artwork)

    explanation = []
    for facet, value in artwork_facets:
        score = signal_map.get((facet, value))
        if score is not None and score > 0.5:
            explanation.append({"facet": facet, "value": value, "score": round(score, 3)})

    explanation.sort(key=lambda x: -x["score"])
    return explanation
