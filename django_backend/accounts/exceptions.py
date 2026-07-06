"""
Custom exception handler for Warungio Marketplace.
Consistent JSON error responses across all APIs.
"""

import logging
import traceback

from django.conf import settings

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Custom exception handler returning consistent JSON errors."""
    response = exception_handler(exc, context)

    if response is not None:
        errors = response.data
        message = extract_error_message(errors)

        custom_response = {
            'success': False,
            'message': message,
            'errors': errors,
            'status_code': response.status_code,
        }
        response.data = custom_response

    # Fallback untuk unhandled exceptions → JSON 500, bukan HTML
    if response is None:
        logger.exception('Unhandled exception in %s: %s', context.get('view', 'unknown'), exc)
        
        response = Response(
            {
                'success': False,
                'message': 'Terjadi kesalahan internal server. Silakan coba lagi nanti.',
                'errors': None,
                'status_code': 500,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        
        if settings.DEBUG:
            response.data['debug'] = {
                'exception': str(exc),
                'traceback': traceback.format_exc().split('\n'),
            }

    return response


def extract_error_message(errors):
    """Extract human-readable error message from DRF errors.
    
    Aggregates ALL field errors into a single message string so users
    can see every validation problem at once (not just the first error).
    """
    if isinstance(errors, dict):
        parts = []
        for field, error_list in errors.items():
            if isinstance(error_list, list) and len(error_list) > 0:
                first_error = error_list[0]
                if isinstance(first_error, dict):
                    # Nested dict error (e.g., non_field_errors with details)
                    nested = extract_error_message(first_error)
                    parts.append(nested)
                else:
                    # Simple field error
                    field_label = field.replace('_', ' ').title()
                    parts.append(f"{field_label}: {str(first_error)}")
            elif isinstance(error_list, str):
                parts.append(str(error_list))
        if parts:
            return ' | '.join(parts)
        return 'Data yang dikirim tidak valid.'
    elif isinstance(errors, list) and len(errors) > 0:
        parts = []
        for error in errors:
            if isinstance(error, dict):
                nested = extract_error_message(error)
                parts.append(nested)
            else:
                parts.append(str(error))
        return ' | '.join(parts) if parts else 'Terjadi kesalahan.'
    return 'Terjadi kesalahan.'


class ServiceUnavailable(Exception):
    """Service unavailable exception."""
    pass


class PaymentError(Exception):
    """Payment processing error."""
    pass


class VerificationError(Exception):
    """User verification error."""
    pass


class DuplicateResourceError(Exception):
    """Duplicate resource error."""
    pass
