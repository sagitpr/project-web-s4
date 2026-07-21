"""
Standardized API response utility for Warungio Marketplace.

Provides consistent JSON response format across all authentication endpoints
to eliminate parsing inconsistencies on the frontend.

Response Format:
    Success: { 'success': True, 'message': str, 'data': dict, 'status_code': int }
    Error:   { 'success': False, 'message': str, 'errors': dict|list, 'status_code': int }

Extended fields used in auth flows:
    - redirect_url: str | None — URL to redirect the user to
    - requires_otp: bool — Whether OTP verification is needed
    - otp_channels: list — Delivery channels used for OTP
    - next_action: str — Next step identifier
    - access: str — JWT access token
    - refresh: str — JWT refresh token
    - user: dict — Serialized user data
"""

from rest_framework.response import Response
from rest_framework import status as http_status
import logging

logger = logging.getLogger(__name__)


def success_response(
    message="Success",
    data=None,
    status_code=http_status.HTTP_200_OK,
    redirect_url=None,
    requires_otp=False,
    **extra_fields,
):
    """
    Build a standardized success response.

    Args:
        message: Human-readable success message
        data: Primary response data (user, tokens, etc.)
        status_code: HTTP status code
        redirect_url: Optional URL for frontend redirect
        requires_otp: Whether OTP verification is required
        **extra_fields: Additional fields to include (otp_channels, next_action, etc.)

    Returns:
        Response object with consistent JSON structure
    """
    response_data = {
        'success': True,
        'message': message,
        'status_code': status_code,
    }

    # Include data if provided
    if data is not None:
        if isinstance(data, dict):
            response_data.update(data)
        else:
            response_data['data'] = data

    # Include redirect_url when applicable
    if redirect_url:
        response_data['redirect_url'] = redirect_url

    # Include requires_otp flag when applicable
    if requires_otp:
        response_data['requires_otp'] = True

    # Include any extra fields
    for key, value in extra_fields.items():
        if value is not None:
            response_data[key] = value

    return Response(response_data, status=status_code)


def error_response(
    message="Terjadi kesalahan",
    errors=None,
    status_code=http_status.HTTP_400_BAD_REQUEST,
    redirect_url=None,
    requires_otp=False,
    **extra_fields,
):
    """
    Build a standardized error response.

    Args:
        message: Human-readable error message
        errors: Detailed error data (field-level errors, etc.)
        status_code: HTTP status code
        redirect_url: Optional URL for frontend redirect (e.g., to OTP page)
        requires_otp: Whether OTP verification is required
        **extra_fields: Additional fields (otp_channels, code, etc.)

    Returns:
        Response object with consistent JSON structure
    """
    response_data = {
        'success': False,
        'message': message,
        'status_code': status_code,
    }

    if errors is not None:
        response_data['errors'] = errors

    # Include redirect_url for flows that need frontend navigation
    if redirect_url:
        response_data['redirect_url'] = redirect_url

    # Include requires_otp flag for unverified user detection
    if requires_otp:
        response_data['requires_otp'] = True
        response_data['needs_verification'] = True

    # Include any extra fields (otp_channels, code, remaining_attempts, etc.)
    for key, value in extra_fields.items():
        if value is not None:
            response_data[key] = value

    return Response(response_data, status=status_code)


def build_auth_response(
    user,
    message,
    status_code=http_status.HTTP_200_OK,
    redirect_url=None,
    requires_otp=False,
    next_action=None,
    **extra_fields,
):
    """
    Build a standardized authentication response with user data and JWT tokens.

    This is the primary response builder for login, OTP verification, and registration flows.
    Ensures consistent 'success' field, user data, and role-based redirect URLs.

    Args:
        user: User model instance
        message: Human-readable message
        status_code: HTTP status code
        redirect_url: URL for frontend redirect (overrides auto-detect)
        requires_otp: Whether OTP is required
        next_action: Next step in the flow
        **extra_fields: Additional fields (access, refresh, otp_channels, etc.)

    Returns:
        Response object with consistent JSON structure
    """
    from .serializers import UserSerializer

    # Auto-detect role-based redirect if not explicitly provided
    if not redirect_url and not requires_otp and user.is_verified:
        if user.role == 'seller':
            redirect_url = '/seller/dashboard/'
        elif user.role == 'buyer':
            redirect_url = '/buyer/home/'
        elif user.role == 'admin':
            redirect_url = '/admin-panel/'
        else:
            redirect_url = '/'

    response_data = {
        'success': True,
        'message': message,
        'status_code': status_code,
        'user': UserSerializer(user).data,
    }

    if redirect_url:
        response_data['redirect_url'] = redirect_url

    if requires_otp:
        response_data['requires_otp'] = True
        response_data['needs_verification'] = True

    if next_action:
        response_data['next_action'] = next_action

    # Include any extra fields (access, refresh, otp_channels, etc.)
    for key, value in extra_fields.items():
        if value is not None:
            response_data[key] = value

    return Response(response_data, status=status_code)
