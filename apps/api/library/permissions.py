from ipaddress import ip_address

from django.conf import settings
from rest_framework.permissions import BasePermission


class IsLocalStudioAdmin(BasePermission):
    message = "O DDJ Content Studio está disponível apenas localmente para administradores."

    def has_permission(self, request, view):
        if not settings.DDJ_CONTENT_STUDIO_ENABLED:
            return False
        if not request.user or not request.user.is_authenticated or not request.user.is_staff:
            return False
        if not settings.DDJ_CONTENT_STUDIO_LOCAL_ONLY:
            return True
        remote = request.META.get("REMOTE_ADDR", "")
        try:
            return ip_address(remote).is_loopback
        except ValueError:
            return False
