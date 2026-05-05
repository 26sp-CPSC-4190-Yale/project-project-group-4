from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import Artwork, Interaction, Match, Message, TasteSignal, UserProfile


def _make_user(username='alice', password='securepass123'):
    user = User.objects.create_user(username=username, password=password)
    token, _ = Token.objects.get_or_create(user=user)
    return user, token


def _auth_client(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register(self):
        """Registration should also create a UserProfile, not just the auth User."""
        res = self.client.post('/api/auth/register/', {
            'username': 'alice', 'email': 'alice@example.com', 'password': 'securepass123',
        }, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertIn('token', res.data)
        self.assertTrue(UserProfile.objects.filter(user__username='alice').exists())

    def test_register_duplicate_username(self):
        User.objects.create_user(username='alice', password='securepass123')
        res = self.client.post('/api/auth/register/', {
            'username': 'alice', 'email': 'alice2@example.com', 'password': 'securepass123',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_login(self):
        User.objects.create_user(username='alice', password='securepass123')
        res = self.client.post('/api/auth/login/', {
            'username': 'alice', 'password': 'securepass123',
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('token', res.data)

    def test_login_wrong_password(self):
        User.objects.create_user(username='alice', password='securepass123')
        res = self.client.post('/api/auth/login/', {
            'username': 'alice', 'password': 'nope',
        }, format='json')
        self.assertEqual(res.status_code, 401)

    def test_logout_deletes_token(self):
        user, token = _make_user()
        res = _auth_client(token).post('/api/auth/logout/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Token.objects.filter(user=user).exists())


class ChangePasswordTests(TestCase):
    def setUp(self):
        self.user, self.token = _make_user(password='OldPass123!')
        self.client = _auth_client(self.token)

    def test_success_returns_new_token(self):
        """Old token must be invalidated — the client has to swap it out after a password change."""
        res = self.client.post('/api/auth/change-password/', {
            'current_password': 'OldPass123!', 'new_password': 'NewPass456!',
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertNotEqual(res.data['token'], self.token.key)

    def test_wrong_current_password(self):
        res = self.client.post('/api/auth/change-password/', {
            'current_password': 'wrong', 'new_password': 'NewPass456!',
        }, format='json')
        self.assertEqual(res.status_code, 400)


class TokenExpiryTests(TestCase):
    def setUp(self):
        self.user, self.token = _make_user()

    @override_settings(TOKEN_EXPIRY_HOURS=24)
    def test_expired_token_rejected_and_deleted(self):
        """Expired tokens should be removed from the DB, not just rejected, so they can't be reused after re-issue."""
        future = timezone.now() + timedelta(hours=25)
        with patch('gallery.auth.timezone') as mock_tz:
            mock_tz.now.return_value = future
            res = _auth_client(self.token).get('/api/profile/me/')
        self.assertEqual(res.status_code, 401)
        self.assertFalse(Token.objects.filter(key=self.token.key).exists())


class ProfileTests(TestCase):
    def setUp(self):
        self.user, self.token = _make_user()
        self.client = _auth_client(self.token)
        UserProfile.objects.get_or_create(user=self.user)

    def test_patch_bio(self):
        res = self.client.patch('/api/profile/me/', {'bio': 'I love Impressionism'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, 'I love Impressionism')

    def test_bio_capped_at_500_chars(self):
        """The view silently truncates long bios rather than rejecting them, so the response is still 200."""
        res = self.client.patch('/api/profile/me/', {'bio': 'x' * 600}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['bio']), 500)


class MatchTests(TestCase):
    def setUp(self):
        self.alice, self.alice_token = _make_user('alice')
        self.bob, self.bob_token = _make_user('bob')
        self.client = _auth_client(self.alice_token)
        self.bob_client = _auth_client(self.bob_token)

    def _match(self, status=Match.STATUS_PENDING):
        return Match.objects.create(
            user1=self.alice, user2=self.bob, similarity=0.8, status=status,
        )

    def test_pending_match_visible_declined_hidden(self):
        self._match(status=Match.STATUS_PENDING)
        self.assertEqual(len(self.client.get('/api/matches/').data), 1)
        Match.objects.all().delete()
        self._match(status=Match.STATUS_DECLINED)
        self.assertEqual(self.client.get('/api/matches/').data, [])

    def test_accept_action(self):
        m = self._match(status=Match.STATUS_REQUESTED)
        m.requested_by = self.alice
        m.save()
        res = self.bob_client.post(f'/api/matches/{self.alice.id}/action/', {'action': 'accept'}, format='json')
        self.assertEqual(res.data['status'], Match.STATUS_ACCEPTED)

    def test_cannot_accept_own_request(self):
        m = self._match(status=Match.STATUS_REQUESTED)
        m.requested_by = self.alice
        m.save()
        res = self.client.post(f'/api/matches/{self.bob.id}/action/', {'action': 'accept'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_unmatch_cascades_to_messages(self):
        """Unmatching should wipe the message history too, not leave orphaned messages behind."""
        self._match(status=Match.STATUS_ACCEPTED)
        Message.objects.create(sender=self.alice, recipient=self.bob, text='Hi!')
        self.client.delete(f'/api/matches/{self.bob.id}/')
        self.assertFalse(Match.objects.filter(user1=self.alice, user2=self.bob).exists())
        self.assertFalse(Message.objects.filter(sender=self.alice, recipient=self.bob).exists())

    def test_facets_shows_shared_taste(self):
        self._match()
        TasteSignal.objects.create(user=self.alice, facet='medium', value='oil', score=0.9)
        TasteSignal.objects.create(user=self.bob, facet='medium', value='oil', score=0.8)
        res = self.client.get(f'/api/matches/{self.bob.id}/facets/')
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['facet'], 'medium')


class MessagingTests(TestCase):
    def setUp(self):
        self.alice, self.alice_token = _make_user('alice')
        self.bob, _ = _make_user('bob')
        self.client = _auth_client(self.alice_token)
        Match.objects.create(user1=self.alice, user2=self.bob, similarity=0.9, status=Match.STATUS_ACCEPTED)

    def test_post_and_retrieve_messages(self):
        self.client.post(f'/api/messages/{self.bob.id}/', {'text': 'First'}, format='json')
        self.client.post(f'/api/messages/{self.bob.id}/', {'text': 'Second'}, format='json')
        res = self.client.get(f'/api/messages/{self.bob.id}/')
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]['text'], 'First')

    def test_messaging_without_match_blocked(self):
        carol = User.objects.create_user(username='carol', password='securepass123')
        res = self.client.post(f'/api/messages/{carol.id}/', {'text': 'Hi'}, format='json')
        self.assertEqual(res.status_code, 403)


class NotificationTests(TestCase):
    def setUp(self):
        self.alice, self.alice_token = _make_user('alice')
        self.bob, _ = _make_user('bob')
        self.client = _auth_client(self.alice_token)

    def test_unseen_match_counted(self):
        Match.objects.create(
            user1=self.alice, user2=self.bob,
            similarity=0.7, status=Match.STATUS_PENDING, seen_by_user1=False,
        )
        self.assertEqual(self.client.get('/api/notifications/').data['new_matches'], 1)

    def test_incoming_request_counted(self):
        Match.objects.create(
            user1=self.alice, user2=self.bob,
            similarity=0.7, status=Match.STATUS_REQUESTED, requested_by=self.bob,
        )
        self.assertEqual(self.client.get('/api/notifications/').data['pending_requests'], 1)


class TasteTests(TestCase):
    def setUp(self):
        self.user, self.token = _make_user()
        self.client = _auth_client(self.token)

    def test_signals_sorted_by_score(self):
        TasteSignal.objects.create(user=self.user, facet='culture', value='French', score=0.7, like_count=3, pass_count=2)
        TasteSignal.objects.create(user=self.user, facet='medium', value='oil', score=0.9, like_count=5, pass_count=1)
        res = self.client.get('/api/taste/me/')
        self.assertEqual(res.data['signals'][0]['facet'], 'medium')


class InteractionTests(TestCase):
    def setUp(self):
        self.user, self.token = _make_user()
        self.client = _auth_client(self.token)

    def _mock_artwork(self, artwork_id=1):
        a = MagicMock()
        a.id = artwork_id
        a.pk = artwork_id
        a.classifiers = a.departments = a.places = MagicMock()
        return a

    @patch('gallery.views.update_taste_signals')
    @patch('gallery.views.Interaction')
    @patch('gallery.views.Artwork')
    def test_like_creates_interaction(self, MockArtwork, MockInteraction, _):
        MockArtwork.objects.get.return_value = self._mock_artwork()
        mock_ix = MagicMock()
        MockInteraction.objects.get_or_create.return_value = (mock_ix, True)
        MockInteraction.objects.filter.return_value.count.return_value = 1
        res = self.client.post('/api/interactions/', {'artwork_id': 1, 'action': 'like'}, format='json')
        self.assertEqual(res.status_code, 201)

    def test_invalid_action_rejected(self):
        res = self.client.post('/api/interactions/', {'artwork_id': 1, 'action': 'favorite'}, format='json')
        self.assertEqual(res.status_code, 400)

    @patch('gallery.views.update_taste_signals')
    @patch('gallery.views.Interaction')
    @patch('gallery.views.Artwork')
    def test_reswipe_updates_existing(self, MockArtwork, MockInteraction, _):
        """Interaction is fully mocked here because passing a MagicMock as a FK causes Django's composite-key path to call int([])."""
        MockArtwork.objects.get.return_value = self._mock_artwork(3)
        mock_ix = MagicMock()
        call_count = [0]

        def _get_or_create(**kwargs):
            call_count[0] += 1
            return mock_ix, call_count[0] == 1

        MockInteraction.objects.get_or_create.side_effect = _get_or_create
        MockInteraction.objects.filter.return_value.count.return_value = 1

        self.client.post('/api/interactions/', {'artwork_id': 3, 'action': 'like'}, format='json')
        res = self.client.post('/api/interactions/', {'artwork_id': 3, 'action': 'pass'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data['created'])

    @patch('gallery.views.update_taste_signals')
    @patch('gallery.views.Interaction')
    def test_delete_interaction(self, MockInteraction, _):
        mock_ix = MagicMock()
        mock_ix.artwork = self._mock_artwork(5)
        mock_ix.action = 'like'
        qs = MagicMock()
        qs.select_related.return_value = qs
        qs.get.return_value = mock_ix
        MockInteraction.objects.select_related.return_value = qs
        MockInteraction.objects.filter.return_value = MagicMock(count=MagicMock(return_value=1))
        res = self.client.delete('/api/interactions/5/')
        self.assertEqual(res.status_code, 204)
