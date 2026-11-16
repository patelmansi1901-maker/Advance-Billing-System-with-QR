
from rest_framework.permissions import BasePermission


class IsDistributor(BasePermission):

    message = "Only authenticated distributors can access this API."

    def has_permission(self, request, view):

        user = request.user

        return (
            user
            and user.is_authenticated
            and user.groups.filter(name="Distributor").exists()
        )
