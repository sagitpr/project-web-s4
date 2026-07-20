"""
Role-based view decorators for Warungio Marketplace.

Provides decorators that enforce role-based access control at the view level,
complementing the RoleBasedRedirectMiddleware for defense in depth.

Usage:
    @buyer_required
    def my_buyer_view(request):
        ...

    @seller_required
    def my_seller_view(request):
        ...
"""

import logging
from functools import wraps
from urllib.parse import quote

from django.shortcuts import redirect

logger = logging.getLogger(__name__)


# ── Redirect paths (single source of truth) ──
_REDIRECT_BUYER = '/buyer/home/'
_REDIRECT_SELLER = '/seller/dashboard/'
_REDIRECT_ADMIN = '/admin-panel/'
_REDIRECT_LOGIN = '/auth/login/'
_REDIRECT_ADMIN_LOGIN = '/admin-panel/login/'
_REDIRECT_HOME = '/'


def buyer_required(view_func):
    """
    Decorator that ensures the user is authenticated AND has role='buyer'.
    
    If unauthenticated → redirect to login page with ?next= parameter.
    If authenticated but not buyer → redirect to role-appropriate dashboard.
    If authenticated buyer → allow access.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'{_REDIRECT_LOGIN}?next={quote(request.path)}')
        
        user = request.user
        role = getattr(user, 'role', None)
        
        if role == 'seller':
            return redirect(_REDIRECT_SELLER)
        if role == 'admin' or user.is_staff:
            return redirect(_REDIRECT_ADMIN)
        if role != 'buyer':
            return redirect(_REDIRECT_HOME)
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def seller_required(view_func):
    """
    Decorator that ensures the user is authenticated AND has role='seller'.
    
    If unauthenticated → redirect to login page with ?next= parameter.
    If authenticated but not seller → redirect to role-appropriate dashboard.
    If authenticated seller → allow access.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'{_REDIRECT_LOGIN}?next={quote(request.path)}')
        
        user = request.user
        role = getattr(user, 'role', None)
        
        if role == 'buyer':
            return redirect(_REDIRECT_BUYER)
        if role == 'admin' or user.is_staff:
            return redirect(_REDIRECT_ADMIN)
        if role != 'seller':
            return redirect(_REDIRECT_HOME)
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def admin_required(view_func):
    """
    Decorator that ensures the user is an admin/staff member.
    Applied to all /admin-panel/ route views.
    
    If unauthenticated → redirect to admin login page with ?next=.
    If authenticated but not admin → redirect to role-appropriate dashboard.
    If authenticated admin → allow access.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'{_REDIRECT_ADMIN_LOGIN}?next={quote(request.path)}')
        
        user = request.user
        role = getattr(user, 'role', None)
        is_staff = user.is_staff or user.is_superuser or role == 'admin'
        
        if not is_staff:
            if role == 'seller':
                return redirect(_REDIRECT_SELLER)
            elif role == 'buyer':
                return redirect(_REDIRECT_BUYER)
            else:
                return redirect(_REDIRECT_HOME)
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
