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
    """Extract human-readable error message from DRF errors."""
    if isinstance(errors, dict):
        for field, error_list in errors.items():
            if isinstance(error_list, list) and len(error_list) > 0:
                error = error_list[0]
                if isinstance(error, dict):
                    return extract_error_message(error)
                return str(error)
            elif isinstance(error_list, str):
                return error_list
        return 'Data yang dikirim tidak valid.'
    elif isinstance(errors, list) and len(errors) > 0:
        error = errors[0]
        if isinstance(error, dict):
            return extract_error_message(error)
        return str(error)
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
