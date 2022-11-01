from rest_framework.permissions import BasePermission, SAFE_METHODS

from users.models import User


class IsShopOwner(BasePermission):
    message = 'only users can edit their profile'

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.subscription_tier == 1

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return request.user == User.objects.get(username=view.kwargs['username'])
