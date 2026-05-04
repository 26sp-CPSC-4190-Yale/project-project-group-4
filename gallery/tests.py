"""
Test suite for gallery views.

Organisation
------------
AuthTests           – register / login / logout
ChangePasswordTests – POST /api/auth/change-password/
TokenExpiryTests    – ExpiringTokenAuthentication rejects stale tokens
ProfileTests        – GET + PATCH /api/profile/me/, profile stats, user photo
MatchTests          – match list, request / accept / decline, unmatch, facets
MessagingTests      – GET + POST /api/messages/<id>/
NotificationTests   – GET /api/notifications/
TasteTests          – GET /api/taste/me/
InteractionTests    – POST + DELETE /api/interactions/ (Artwork queryset mocked)
ArtworkTests        – GET /api/artworks/, /api/artwork/<id>/ (queryset mocked)
LikedArtworksTests  – GET /api/liked/ (queryset mocked)

For views that query the read-only Yale LUX artwork database (Artwork and its
related unmanaged models), we patch the relevant querysets at the view module
level so the test suite runs without the SQLite data file.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import Artwork, Interaction, Match, Message, TasteSignal, UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username='alice', password='securepass123'):
    """Create a user and return (user, token)."""
    user = User.objects.create_user(username=username, password=password)
    token, _ = Token.objects.get_or_create(user=user)
    return user, token


def _auth_client(token):
    """Return an APIClient pre-loaded with the given token."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class AuthTests(TestCase):
    """Tests for /api/auth/register/, login/, and logout/."""

    def setUp(self):
        self.client = APIClient()

    # -- register --

    def test_register_success_creates_user_and_returns_token(self):
        """Successful registration returns HTTP 201 with a token."""
        res = self.client.post('/api/auth/register/', {
            'username': 'alice', 'email': 'alice@example.com', 'password': 'securepass123',
        }, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertIn('token', res.data)
        self.assertTrue(User.objects.filter(username='alice').exists())

    def test_register_creates_user_profile(self):
        """Registration also creates an associated UserProfile row."""
        self.client.post('/api/auth/register/', {
            'username': 'alice', 'email': 'alice@example.com', 'password': 'securepass123',
        }, format='json')
        user = User.objects.get(username='alice')
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_register_duplicate_username_returns_400(self):
        """Registering a username that already exists is rejected."""
        User.objects.create_user(username='alice', password='securepass123')
        res = self.client.post('/api/auth/register/', {
            'username': 'alice', 'email': 'alice2@example.com', 'password': 'securepass123',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_register_password_too_short_returns_400(self):
        """Password shorter than 8 characters is rejected by the serializer."""
        res = self.client.post('/api/auth/register/', {
            'username': 'bob', 'email': 'bob@example.com', 'password': 'short',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_register_missing_username_returns_400(self):
        """Missing required username field returns a validation error."""
        res = self.client.post('/api/auth/register/', {
            'email': 'x@example.com', 'password': 'securepass123',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    # -- login --

    def test_login_valid_credentials_returns_token(self):
        """Correct credentials return HTTP 200 and a token."""
        User.objects.create_user(username='alice', password='securepass123')
        res = self.client.post('/api/auth/login/', {
            'username': 'alice', 'password': 'securepass123',
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('token', res.data)
        self.assertIn('user', res.data)

    def test_login_wrong_password_returns_401(self):
        """Wrong password returns 401 Unauthorized."""
        User.objects.create_user(username='alice', password='securepass123')
        res = self.client.post('/api/auth/login/', {
            'username': 'alice', 'password': 'wrongpassword',
        }, format='json')
        self.assertEqual(res.status_code, 401)

    def test_login_unknown_user_returns_401(self):
        """Login attempt for a non-existent username returns 401."""
        res = self.client.post('/api/auth/login/', {
            'username': 'nobody', 'password': 'securepass123',
        }, format='json')
        self.assertEqual(res.status_code, 401)

    def test_login_reuses_existing_token(self):
        """Logging in twice returns the same token (get_or_create)."""
        User.objects.create_user(username='alice', password='securepass123')
        r1 = self.client.post('/api/auth/login/', {
            'username': 'alice', 'password': 'securepass123',
        }, format='json')
        r2 = self.client.post('/api/auth/login/', {
            'username': 'alice', 'password': 'securepass123',
        }, format='json')
        self.assertEqual(r1.data['token'], r2.data['token'])

    # -- logout --

    def test_logout_deletes_token(self):
        """Authenticated logout deletes the server-side token."""
        user, token = _make_user()
        client = _auth_client(token)
        res = client.post('/api/auth/logout/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Token.objects.filter(user=user).exists())

    def test_logout_without_token_returns_401(self):
        """Unauthenticated logout attempt returns 401."""
        res = self.client.post('/api/auth/logout/')
        self.assertEqual(res.status_code, 401)

    def test_logout_with_invalid_token_returns_401(self):
        """Garbage token value returns 401."""
        self.client.credentials(HTTP_AUTHORIZATION='Token notavalidtoken')
        res = self.client.post('/api/auth/logout/')
        self.assertEqual(res.status_code, 401)


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------

class ChangePasswordTests(TestCase):
    """Tests for POST /api/auth/change-password/."""

    def setUp(self):
        self.user, self.token = _make_user(password='OldPass123!')
        self.client = _auth_client(self.token)

    def test_success_returns_new_token(self):
        """Valid password change returns HTTP 200 with a fresh token."""
        res = self.client.post('/api/auth/change-password/', {
            'current_password': 'OldPass123!',
            'new_password': 'NewPass456!',
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('token', res.data)
        # New token must differ from the old one
        self.assertNotEqual(res.data['token'], self.token.key)

    def test_success_old_token_is_deleted(self):
        """After a password change the original token no longer exists."""
        self.client.post('/api/auth/change-password/', {
            'current_password': 'OldPass123!',
            'new_password': 'NewPass456!',
        }, format='json')
        self.assertFalse(Token.objects.filter(key=self.token.key).exists())

    def test_success_new_password_works_for_login(self):
        """After changing password the user can log in with the new password."""
        self.client.post('/api/auth/change-password/', {
            'current_password': 'OldPass123!',
            'new_password': 'NewPass456!',
        }, format='json')
        plain = APIClient()
        res = plain.post('/api/auth/login/', {
            'username': 'alice', 'password': 'NewPass456!',
        }, format='json')
        self.assertEqual(res.status_code, 200)

    def test_wrong_current_password_returns_400(self):
        """Supplying the wrong current password returns 400."""
        res = self.client.post('/api/auth/change-password/', {
            'current_password': 'wrongpassword',
            'new_password': 'NewPass456!',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_missing_current_password_returns_400(self):
        """Omitting current_password returns 400."""
        res = self.client.post('/api/auth/change-password/', {
            'new_password': 'NewPass456!',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_missing_new_password_returns_400(self):
        """Omitting new_password returns 400."""
        res = self.client.post('/api/auth/change-password/', {
            'current_password': 'OldPass123!',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_new_password_too_common_returns_400(self):
        """Django's CommonPasswordValidator rejects trivial passwords."""
        res = self.client.post('/api/auth/change-password/', {
            'current_password': 'OldPass123!',
            'new_password': 'password',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_unauthenticated_returns_401(self):
        """Change-password without a token returns 401."""
        res = APIClient().post('/api/auth/change-password/', {
            'current_password': 'OldPass123!',
            'new_password': 'NewPass456!',
        }, format='json')
        self.assertEqual(res.status_code, 401)


# ---------------------------------------------------------------------------
# Token expiry
# ---------------------------------------------------------------------------

class TokenExpiryTests(TestCase):
    """Tests for ExpiringTokenAuthentication."""

    def setUp(self):
        self.user, self.token = _make_user()

    @override_settings(TOKEN_EXPIRY_HOURS=24)
    def test_fresh_token_is_accepted(self):
        """A just-created token passes authentication."""
        client = _auth_client(self.token)
        res = client.get('/api/profile/me/')
        self.assertNotEqual(res.status_code, 401)

    @override_settings(TOKEN_EXPIRY_HOURS=24)
    def test_expired_token_returns_401(self):
        """A token older than TOKEN_EXPIRY_HOURS is rejected with 401."""
        future = timezone.now() + timedelta(hours=25)
        with patch('gallery.auth.timezone') as mock_tz:
            mock_tz.now.return_value = future
            client = _auth_client(self.token)
            res = client.get('/api/profile/me/')
        self.assertEqual(res.status_code, 401)

    @override_settings(TOKEN_EXPIRY_HOURS=24)
    def test_expired_token_is_deleted_from_db(self):
        """When a token is rejected for expiry it is removed from the database."""
        future = timezone.now() + timedelta(hours=25)
        with patch('gallery.auth.timezone') as mock_tz:
            mock_tz.now.return_value = future
            client = _auth_client(self.token)
            client.get('/api/profile/me/')
        self.assertFalse(Token.objects.filter(key=self.token.key).exists())

    @override_settings(TOKEN_EXPIRY_HOURS=24)
    def test_login_resets_token_age(self):
        """
        Logging in after expiry deletes the old token and issues a new one,
        so the new token is immediately usable.
        """
        future = timezone.now() + timedelta(hours=25)
        with patch('gallery.auth.timezone') as mock_tz:
            mock_tz.now.return_value = future
            _auth_client(self.token).get('/api/profile/me/')  # expire + delete token

        plain = APIClient()
        res = plain.post('/api/auth/login/', {
            'username': 'alice', 'password': 'securepass123',
        }, format='json')
        self.assertEqual(res.status_code, 200)
        new_token_key = res.data['token']
        self.assertNotEqual(new_token_key, self.token.key)


# ---------------------------------------------------------------------------
# User profiles
# ---------------------------------------------------------------------------

class ProfileTests(TestCase):
    """Tests for /api/profile/me/ and /api/profile/stats/."""

    def setUp(self):
        self.user, self.token = _make_user()
        self.client = _auth_client(self.token)
        UserProfile.objects.get_or_create(user=self.user)

    def test_get_profile_returns_bio_and_photo_flag(self):
        """GET /api/profile/me/ returns the user's bio and has_photo flag."""
        res = self.client.get('/api/profile/me/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('bio', res.data)
        self.assertIn('has_photo', res.data)

    def test_patch_profile_updates_bio(self):
        """PATCH with a bio field persists the new bio."""
        res = self.client.patch('/api/profile/me/', {'bio': 'I love Impressionism'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['bio'], 'I love Impressionism')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, 'I love Impressionism')

    def test_patch_profile_bio_truncated_to_500_chars(self):
        """A bio longer than 500 characters is silently truncated."""
        long_bio = 'x' * 600
        res = self.client.patch('/api/profile/me/', {'bio': long_bio}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['bio']), 500)

    def test_profile_requires_authentication(self):
        """Unauthenticated access to the profile endpoint returns 401."""
        res = APIClient().get('/api/profile/me/')
        self.assertEqual(res.status_code, 401)

    def test_profile_stats_returns_expected_fields(self):
        """GET /api/profile/stats/ returns like/pass counts and dates."""
        res = self.client.get('/api/profile/stats/')
        self.assertEqual(res.status_code, 200)
        for field in ('total_likes', 'total_passes', 'like_rate', 'date_joined'):
            self.assertIn(field, res.data)

    def test_profile_stats_with_no_interactions(self):
        """A new user with no swipes has like_rate of 0.0."""
        res = self.client.get('/api/profile/stats/')
        self.assertEqual(res.data['like_rate'], 0.0)

    def test_user_photo_not_found_returns_404(self):
        """Requesting a photo for a user with no photo stored returns 404."""
        res = self.client.get(f'/api/profile/photo/{self.user.id}/')
        self.assertEqual(res.status_code, 404)

    def test_user_photo_unknown_user_returns_404(self):
        """Requesting a photo for a non-existent user ID returns 404."""
        res = self.client.get('/api/profile/photo/99999/')
        self.assertEqual(res.status_code, 404)


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------

class MatchTests(TestCase):
    """Tests for /api/matches/ and related match-action endpoints."""

    def setUp(self):
        self.alice, self.alice_token = _make_user('alice')
        self.bob, self.bob_token = _make_user('bob')
        self.client = _auth_client(self.alice_token)
        self.bob_client = _auth_client(self.bob_token)

    def _create_match(self, status=Match.STATUS_PENDING):
        return Match.objects.create(
            user1=self.alice, user2=self.bob, similarity=0.8, status=status,
        )

    # -- match list --

    def test_match_list_empty(self):
        """No matches returns an empty list."""
        res = self.client.get('/api/matches/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, [])

    def test_match_list_includes_pending_match(self):
        """A pending match appears in the list."""
        self._create_match()
        res = self.client.get('/api/matches/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['user']['username'], 'bob')

    def test_match_list_excludes_declined_match(self):
        """Declined matches are filtered out of the list."""
        self._create_match(status=Match.STATUS_DECLINED)
        res = self.client.get('/api/matches/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, [])

    def test_match_list_visible_from_both_sides(self):
        """Both users can see the match in their own list."""
        self._create_match()
        res = self.bob_client.get('/api/matches/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

    # -- match actions --

    def test_match_action_request(self):
        """Requesting a match transitions status to 'requested'."""
        self._create_match()
        res = self.client.post(f'/api/matches/{self.bob.id}/action/', {
            'action': 'request',
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], Match.STATUS_REQUESTED)

    def test_match_action_accept(self):
        """Accepting an incoming request transitions status to 'accepted'."""
        match = self._create_match(status=Match.STATUS_REQUESTED)
        match.requested_by = self.alice
        match.save()
        # Bob accepts Alice's request
        res = self.bob_client.post(f'/api/matches/{self.alice.id}/action/', {
            'action': 'accept',
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], Match.STATUS_ACCEPTED)

    def test_match_action_decline(self):
        """Declining an incoming request transitions status to 'declined'."""
        match = self._create_match(status=Match.STATUS_REQUESTED)
        match.requested_by = self.alice
        match.save()
        res = self.bob_client.post(f'/api/matches/{self.alice.id}/action/', {
            'action': 'decline',
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], Match.STATUS_DECLINED)

    def test_match_action_invalid_action_returns_400(self):
        """An unrecognised action value returns 400."""
        self._create_match()
        res = self.client.post(f'/api/matches/{self.bob.id}/action/', {
            'action': 'hug',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_match_action_no_match_returns_404(self):
        """Acting on a non-existent match returns 404."""
        carol = User.objects.create_user(username='carol', password='securepass123')
        res = self.client.post(f'/api/matches/{carol.id}/action/', {
            'action': 'request',
        }, format='json')
        self.assertEqual(res.status_code, 404)

    def test_cannot_accept_own_request(self):
        """The user who sent the request cannot accept it themselves."""
        match = self._create_match(status=Match.STATUS_REQUESTED)
        match.requested_by = self.alice
        match.save()
        res = self.client.post(f'/api/matches/{self.bob.id}/action/', {
            'action': 'accept',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    # -- unmatch --

    def test_unmatch_deletes_match(self):
        """DELETE /api/matches/<id>/ removes the match record."""
        self._create_match()
        res = self.client.delete(f'/api/matches/{self.bob.id}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Match.objects.filter(user1=self.alice, user2=self.bob).exists())

    def test_unmatch_deletes_messages(self):
        """Unmatching also deletes any messages between the two users."""
        self._create_match(status=Match.STATUS_ACCEPTED)
        Message.objects.create(sender=self.alice, recipient=self.bob, text='Hi!')
        self.client.delete(f'/api/matches/{self.bob.id}/')
        self.assertFalse(Message.objects.filter(sender=self.alice, recipient=self.bob).exists())

    # -- match facets --

    def test_match_facets_no_signals_returns_empty(self):
        """Facets endpoint returns empty list when neither user has taste signals."""
        self._create_match()
        res = self.client.get(f'/api/matches/{self.bob.id}/facets/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, [])

    def test_match_facets_with_shared_signals(self):
        """Shared taste signals appear in the facets response."""
        self._create_match()
        TasteSignal.objects.create(user=self.alice, facet='medium', value='oil', score=0.9)
        TasteSignal.objects.create(user=self.bob, facet='medium', value='oil', score=0.8)
        res = self.client.get(f'/api/matches/{self.bob.id}/facets/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['facet'], 'medium')

    def test_match_facets_no_match_returns_404(self):
        """Requesting facets for a non-existent match returns 404."""
        carol = User.objects.create_user(username='carol', password='securepass123')
        res = self.client.get(f'/api/matches/{carol.id}/facets/')
        self.assertEqual(res.status_code, 404)


# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------

class MessagingTests(TestCase):
    """Tests for GET + POST /api/messages/<user_id>/."""

    def setUp(self):
        self.alice, self.alice_token = _make_user('alice')
        self.bob, self.bob_token = _make_user('bob')
        self.client = _auth_client(self.alice_token)
        # Create an accepted match so messaging is allowed
        Match.objects.create(
            user1=self.alice, user2=self.bob,
            similarity=0.9, status=Match.STATUS_ACCEPTED,
        )

    def test_get_empty_conversation(self):
        """No messages returns an empty list."""
        res = self.client.get(f'/api/messages/{self.bob.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, [])

    def test_post_message_creates_message(self):
        """Posting a message creates it and returns HTTP 201."""
        res = self.client.post(f'/api/messages/{self.bob.id}/', {
            'text': 'Hello Bob!',
        }, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['text'], 'Hello Bob!')
        self.assertTrue(Message.objects.filter(sender=self.alice, recipient=self.bob).exists())

    def test_get_conversation_returns_messages_in_order(self):
        """Messages are returned in chronological order."""
        Message.objects.create(sender=self.alice, recipient=self.bob, text='First')
        Message.objects.create(sender=self.bob, recipient=self.alice, text='Second')
        res = self.client.get(f'/api/messages/{self.bob.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]['text'], 'First')

    def test_post_empty_message_returns_400(self):
        """Posting a blank message returns 400."""
        res = self.client.post(f'/api/messages/{self.bob.id}/', {
            'text': '   ',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_post_message_too_long_returns_400(self):
        """A message exceeding 5000 characters returns 400."""
        res = self.client.post(f'/api/messages/{self.bob.id}/', {
            'text': 'x' * 5001,
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_message_without_accepted_match_returns_403(self):
        """Cannot message a user without an accepted match."""
        carol = User.objects.create_user(username='carol', password='securepass123')
        res = self.client.post(f'/api/messages/{carol.id}/', {
            'text': 'Hi Carol',
        }, format='json')
        self.assertEqual(res.status_code, 403)

    def test_message_non_existent_user_returns_404(self):
        """Messaging a user ID that doesn't exist returns 404."""
        res = self.client.post('/api/messages/99999/', {'text': 'hi'}, format='json')
        self.assertEqual(res.status_code, 404)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class NotificationTests(TestCase):
    """Tests for GET /api/notifications/."""

    def setUp(self):
        self.alice, self.alice_token = _make_user('alice')
        self.bob, _ = _make_user('bob')
        self.client = _auth_client(self.alice_token)

    def test_no_notifications(self):
        """User with no activity has zero counts for all notification types."""
        res = self.client.get('/api/notifications/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['new_matches'], 0)
        self.assertEqual(res.data['pending_requests'], 0)

    def test_unseen_pending_match_counted(self):
        """A new unseen pending match increments new_matches."""
        Match.objects.create(
            user1=self.alice, user2=self.bob,
            similarity=0.7,
            status=Match.STATUS_PENDING,
            seen_by_user1=False,
        )
        res = self.client.get('/api/notifications/')
        self.assertEqual(res.data['new_matches'], 1)

    def test_incoming_request_counted(self):
        """An incoming match request increments pending_requests."""
        m = Match.objects.create(
            user1=self.alice, user2=self.bob,
            similarity=0.7,
            status=Match.STATUS_REQUESTED,
            requested_by=self.bob,
        )
        res = self.client.get('/api/notifications/')
        self.assertEqual(res.data['pending_requests'], 1)

    def test_notifications_requires_authentication(self):
        """Unauthenticated request returns 401."""
        res = APIClient().get('/api/notifications/')
        self.assertEqual(res.status_code, 401)


# ---------------------------------------------------------------------------
# Taste signals
# ---------------------------------------------------------------------------

class TasteTests(TestCase):
    """Tests for GET /api/taste/me/."""

    def setUp(self):
        self.user, self.token = _make_user()
        self.client = _auth_client(self.token)

    def test_my_taste_no_signals(self):
        """User with no taste signals gets an empty signals list."""
        res = self.client.get('/api/taste/me/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['signals'], [])

    def test_my_taste_returns_top_signals(self):
        """Created TasteSignal rows appear in the taste response."""
        TasteSignal.objects.create(
            user=self.user, facet='medium', value='oil', score=0.9,
            like_count=5, pass_count=1,
        )
        TasteSignal.objects.create(
            user=self.user, facet='culture', value='French', score=0.7,
            like_count=3, pass_count=2,
        )
        res = self.client.get('/api/taste/me/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['signals']), 2)
        # Highest score first
        self.assertEqual(res.data['signals'][0]['facet'], 'medium')

    def test_my_taste_requires_authentication(self):
        """Unauthenticated access returns 401."""
        res = APIClient().get('/api/taste/me/')
        self.assertEqual(res.status_code, 401)


# ---------------------------------------------------------------------------
# Interactions  (Artwork queryset patched — unmanaged model)
# ---------------------------------------------------------------------------

class InteractionTests(TestCase):
    """
    Tests for POST /api/interactions/ and DELETE /api/interactions/<artwork_id>/.

    The Artwork model is backed by the read-only Yale LUX SQLite database that
    does not exist in the test environment, so Artwork.objects is patched at the
    view module level for these tests.
    """

    def setUp(self):
        self.user, self.token = _make_user()
        self.client = _auth_client(self.token)

    def _make_mock_artwork(self, artwork_id=1):
        """Return a MagicMock that quacks like an Artwork instance."""
        artwork = MagicMock()
        artwork.id = artwork_id
        artwork.pk = artwork_id
        artwork.classifiers = MagicMock()
        artwork.departments = MagicMock()
        artwork.places = MagicMock()
        return artwork

    @patch('gallery.views.update_taste_signals')
    @patch('gallery.views.Interaction')
    @patch('gallery.views.Artwork')
    def test_record_like_creates_interaction(self, MockArtwork, MockInteraction, _mock_update):
        """POST with action=like creates an Interaction and returns 201."""
        mock_artwork = self._make_mock_artwork(1)
        MockArtwork.objects.get.return_value = mock_artwork
        mock_interaction = MagicMock()
        MockInteraction.objects.get_or_create.return_value = (mock_interaction, True)
        MockInteraction.objects.filter.return_value.count.return_value = 1

        res = self.client.post('/api/interactions/', {
            'artwork_id': 1, 'action': 'like',
        }, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data['created'])

    @patch('gallery.views.update_taste_signals')
    @patch('gallery.views.Interaction')
    @patch('gallery.views.Artwork')
    def test_record_pass_creates_interaction(self, MockArtwork, MockInteraction, _mock_update):
        """POST with action=pass creates an Interaction and returns 201."""
        mock_artwork = self._make_mock_artwork(2)
        MockArtwork.objects.get.return_value = mock_artwork
        mock_interaction = MagicMock()
        MockInteraction.objects.get_or_create.return_value = (mock_interaction, True)
        MockInteraction.objects.filter.return_value.count.return_value = 1

        res = self.client.post('/api/interactions/', {
            'artwork_id': 2, 'action': 'pass',
        }, format='json')
        self.assertEqual(res.status_code, 201)

    def test_invalid_action_returns_400(self):
        """An action value other than 'like' or 'pass' is rejected before artwork lookup."""
        res = self.client.post('/api/interactions/', {
            'artwork_id': 1, 'action': 'favorite',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    @patch('gallery.views.Artwork')
    def test_artwork_not_found_returns_404(self, MockArtwork):
        """Interacting with a non-existent artwork_id returns 404."""
        from gallery.models import Artwork as RealArtwork
        MockArtwork.objects.get.side_effect = RealArtwork.DoesNotExist
        MockArtwork.DoesNotExist = RealArtwork.DoesNotExist

        res = self.client.post('/api/interactions/', {
            'artwork_id': 99999, 'action': 'like',
        }, format='json')
        self.assertEqual(res.status_code, 404)

    @patch('gallery.views.update_taste_signals')
    @patch('gallery.views.Interaction')
    @patch('gallery.views.Artwork')
    def test_re_swipe_updates_interaction(self, MockArtwork, MockInteraction, _mock_update):
        """Swiping again on the same artwork with a different action updates the record."""
        # Interaction.objects is mocked entirely here because passing a MagicMock as
        # the artwork FK value causes Django 6's composite-FK path to call int([]),
        # which fails.  By mocking get_or_create we verify the re-swipe logic without
        # any FK resolution.
        mock_artwork = self._make_mock_artwork(3)
        MockArtwork.objects.get.return_value = mock_artwork

        mock_interaction = MagicMock()
        mock_interaction.action = 'like'
        call_count = [0]

        def _get_or_create(**kwargs):
            call_count[0] += 1
            created = call_count[0] == 1
            return mock_interaction, created

        MockInteraction.objects.get_or_create.side_effect = _get_or_create
        MockInteraction.objects.filter.return_value.count.return_value = 1

        # First swipe – newly created
        r1 = self.client.post('/api/interactions/', {
            'artwork_id': 3, 'action': 'like',
        }, format='json')
        self.assertEqual(r1.status_code, 201)

        # Re-swipe – same interaction found, action updated
        res = self.client.post('/api/interactions/', {
            'artwork_id': 3, 'action': 'pass',
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data['created'])

    def test_record_interaction_requires_authentication(self):
        """Unauthenticated swipe returns 401."""
        res = APIClient().post('/api/interactions/', {
            'artwork_id': 1, 'action': 'like',
        }, format='json')
        self.assertEqual(res.status_code, 401)

    @patch('gallery.views.update_taste_signals')
    @patch('gallery.views.Interaction')
    def test_delete_interaction_success(self, MockInteraction, _mock_update):
        """DELETE /api/interactions/<id>/ removes the interaction and returns 204."""
        mock_artwork = self._make_mock_artwork(5)
        mock_interaction = MagicMock()
        mock_interaction.artwork = mock_artwork
        mock_interaction.action = 'like'

        qs = MagicMock()
        qs.select_related.return_value = qs
        qs.get.return_value = mock_interaction
        MockInteraction.objects.select_related.return_value = qs
        MockInteraction.objects.filter.return_value = MagicMock(count=MagicMock(return_value=1))

        res = self.client.delete('/api/interactions/5/')
        self.assertEqual(res.status_code, 204)

    @patch('gallery.views.Interaction')
    def test_delete_interaction_not_found_returns_404(self, MockInteraction):
        """Deleting a non-existent interaction returns 404."""
        from gallery.models import Interaction as RealInteraction
        qs = MagicMock()
        qs.select_related.return_value = qs
        qs.get.side_effect = RealInteraction.DoesNotExist
        MockInteraction.objects.select_related.return_value = qs
        MockInteraction.DoesNotExist = RealInteraction.DoesNotExist

        res = self.client.delete('/api/interactions/9999/')
        self.assertEqual(res.status_code, 404)


# ---------------------------------------------------------------------------
# Artwork endpoints  (Artwork queryset patched)
# ---------------------------------------------------------------------------

class ArtworkTests(TestCase):
    """
    Tests for GET /api/artworks/ and GET /api/artwork/<id>/.

    Artwork is an unmanaged model; its QuerySet is patched so these tests run
    without the SQLite data file.
    """

    def setUp(self):
        self.user, self.token = _make_user()
        self.client = _auth_client(self.token)

    def _make_mock_artwork(self, artwork_id=1, label='Test Artwork'):
        a = MagicMock()
        a.id = artwork_id
        a.label = label
        a.accession_no = f'ACC-{artwork_id}'
        a.date = '1900'
        a.classifiers = MagicMock()
        a.departments = MagicMock()
        a.places = MagicMock()
        return a

    @patch('gallery.views.Artwork')
    @patch('gallery.views.Interaction')
    def test_artwork_list_returns_results(self, MockInteraction, MockArtwork):
        """GET /api/artworks/ returns a results list."""
        mock_artwork = self._make_mock_artwork()
        MockInteraction.objects.filter.return_value.values.return_value = []
        qs = MagicMock()
        qs.exclude.return_value = qs
        qs.order_by.return_value.__getitem__ = MagicMock(return_value=[mock_artwork])
        MockArtwork.objects.exclude.return_value = qs

        res = self.client.get('/api/artworks/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('results', res.data)

    @patch('gallery.views.Artwork')
    def test_artwork_detail_returns_data(self, MockArtwork):
        """GET /api/artwork/<id>/ returns the artwork fields."""
        mock_artwork = self._make_mock_artwork(42)
        MockArtwork.objects.get.return_value = mock_artwork

        # ArtworkDetailSerializer imports Interaction from gallery.serializers,
        # not gallery.views, so the patch target must match the import location.
        with patch('gallery.serializers.Interaction') as MockInteraction:
            MockInteraction.objects.filter.return_value.count.return_value = 0
            res = self.client.get('/api/artwork/42/')

        self.assertEqual(res.status_code, 200)

    @patch('gallery.views.Artwork')
    def test_artwork_detail_not_found_returns_404(self, MockArtwork):
        """Requesting a non-existent artwork ID returns 404."""
        from gallery.models import Artwork as RealArtwork
        MockArtwork.objects.get.side_effect = RealArtwork.DoesNotExist
        MockArtwork.DoesNotExist = RealArtwork.DoesNotExist

        res = self.client.get('/api/artwork/99999/')
        self.assertEqual(res.status_code, 404)


# ---------------------------------------------------------------------------
# Liked artworks  (queryset patched)
# ---------------------------------------------------------------------------

class LikedArtworksTests(TestCase):
    """Tests for GET /api/liked/ (requires Interaction->Artwork join, patched)."""

    def setUp(self):
        self.user, self.token = _make_user()
        self.client = _auth_client(self.token)

    @patch('gallery.views.Interaction')
    def test_liked_artworks_empty(self, MockInteraction):
        """User with no likes gets an empty results list with count 0."""
        qs = MagicMock()
        qs.select_related.return_value = qs
        qs.order_by.return_value = qs
        qs.count.return_value = 0
        qs.__getitem__ = MagicMock(return_value=[])
        MockInteraction.objects.filter.return_value = qs

        res = self.client.get('/api/liked/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('count', res.data)
        self.assertIn('results', res.data)

    def test_liked_artworks_requires_authentication(self):
        """Unauthenticated request returns 401."""
        res = APIClient().get('/api/liked/')
        self.assertEqual(res.status_code, 401)

    @patch('gallery.views.Interaction')
    def test_liked_artworks_pagination_params(self, MockInteraction):
        """limit and offset query parameters are reflected in the response."""
        qs = MagicMock()
        qs.select_related.return_value = qs
        qs.order_by.return_value = qs
        qs.count.return_value = 0
        qs.__getitem__ = MagicMock(return_value=[])
        MockInteraction.objects.filter.return_value = qs

        res = self.client.get('/api/liked/?limit=5&offset=10')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['limit'], 5)
        self.assertEqual(res.data['offset'], 10)
