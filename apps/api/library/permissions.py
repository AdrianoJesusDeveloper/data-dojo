from ipaddress import ip_address

from django.conf import settings
from rest_framework.permissions import BasePermission

from core.permissions import is_administrative_user


class IsLocalStudioAdmin(BasePermission):
    message = "O DDJ Content Studio está disponível apenas localmente para administradores."

    def has_permission(self, request, view):
        if not settings.DDJ_CONTENT_STUDIO_ENABLED:
            return False
        if not is_administrative_user(request.user):
            return False
        if not settings.DDJ_CONTENT_STUDIO_LOCAL_ONLY:
            return True
        remote = request.META.get("REMOTE_ADDR", "")
        try:
            address = ip_address(remote)
        except ValueError:
            return False
        if address.is_loopback:
            return True
        return remote in settings.DDJ_CONTENT_STUDIO_TRUSTED_IPS
