from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import User

PURCHASING_ROLES = {
    User.Role.ADMIN, User.Role.MANAGER, User.Role.PHARMACIST, User.Role.STOCK,
}


class CanManagePurchasing(BasePermission):
    """Any signed-in user can read; only buying roles can change purchasing data."""

    message = "Your role cannot create or change purchasing documents."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_superuser or user.role in PURCHASING_ROLES
