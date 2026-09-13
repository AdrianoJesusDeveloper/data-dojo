from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_administrative_user(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_staff or user.is_superuser)
    )


class IsAdministrativeUser(BasePermission):
    message = "Esta área está disponível apenas para administradores."

    def has_permission(self, request, view):
        return is_administrative_user(request.user)


class IsAdministrativeUserOrReadOnly(IsAdministrativeUser):
    """Preserve public reads while restricting writes to administrators."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or super().has_permission(request, view)
