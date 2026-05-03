from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

# How many hours before a token is considered expired. Override in settings.py.
TOKEN_EXPIRY_HOURS = getattr(settings, 'TOKEN_EXPIRY_HOURS', 24)


class ExpiringTokenAuthentication(TokenAuthentication):
    """
    Extends DRF's TokenAuthentication to reject tokens older than TOKEN_EXPIRY_HOURS.

    When a token expires it is deleted server-side. The client receives a 401
    and must log in again to obtain a fresh token.
    """

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        age = timezone.now() - token.created
        if age > timedelta(hours=TOKEN_EXPIRY_HOURS):
            token.delete()
            raise AuthenticationFailed(
                'Token has expired. Please log in again.',
                code='token_expired',
            )
        return user, token
