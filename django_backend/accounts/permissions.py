"""
Custom permissions for Warungio Marketplace.
Role-based access control (Buyer, Seller, Admin).
"""

from rest_framework import permissions


class IsBuyer(permissions.BasePermission):
    """Allow access only to buyers."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'buyer'


class IsSeller(permissions.BasePermission):
    """Allow access only to sellers."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'seller'


class IsAdmin(permissions.BasePermission):
    """Allow access only to admins."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role == 'admin' or request.user.is_superuser
        )


class IsStoreOwner(permissions.BasePermission):
    """Allow access only to the store owner."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role == 'seller' or request.user.role == 'admin'
        )

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'store'):
            return obj.store.user == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class IsOrderOwner(permissions.BasePermission):
    """Allow access only to order owner."""
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or (
            hasattr(obj, 'store') and obj.store.user == request.user
        )


class IsVerifiedUser(permissions.BasePermission):
    """Allow access only to verified users."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_verified


class ReadOnly(permissions.BasePermission):
    """Allow read-only access."""
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Allow edit only to owner."""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user
