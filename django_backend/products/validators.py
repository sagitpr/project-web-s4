"""
File upload validators for Warungio Marketplace.
Runtime MIME type and extension validation for all image uploads.
"""

import logging
from django.conf import settings
from rest_framework import serializers

logger = logging.getLogger(__name__)


# Map of PIL format names to MIME types
PIL_MIME_MAP = {
    'JPEG': 'image/jpeg',
    'PNG': 'image/png',
    'GIF': 'image/gif',
    'WEBP': 'image/webp',
    'BMP': 'image/bmp',
}


def validate_image_file(value):
    """
    Validate uploaded image file MIME type and extension at runtime.
    
    Django's ImageField uses Pillow to verify the file is an image,
    but this validator adds an extra layer of MIME type and extension checking
    to prevent files with manipulated content from being accepted.
    
    Uses PIL/Pillow (already installed) to detect the actual image format
    by reading the file header bytes.
    
    Usage in serializers:
        def validate_product_photo(self, value):
            return validate_image_file(value)
    """
    if value is None:
        return value

    # Check file extension
    ext = value.name.split('.')[-1].lower() if '.' in value.name else ''
    allowed_extensions = getattr(settings, 'ALLOWED_IMAGE_EXTENSIONS', 
                                  ['jpg', 'jpeg', 'png', 'gif', 'webp'])
    
    if ext and ext not in allowed_extensions:
        raise serializers.ValidationError(
            f"Ekstensi file '{ext}' tidak diizinkan. "
            f"Ekstensi yang diizinkan: {', '.join(allowed_extensions)}"
        )

    # Detect actual image format using Pillow (already installed)
    try:
        from PIL import Image
        
        value.seek(0)
        # Use PIL to detect image format from file content (not extension)
        image = Image.open(value)
        detected_format = image.format  # e.g. 'JPEG', 'PNG', 'GIF', 'WEBP'
        image.verify()  # Verify it's a valid image without decoding
        value.seek(0)  # Reset file pointer for downstream usage
        
        if detected_format is None:
            raise serializers.ValidationError(
                "File yang diunggah bukan gambar yang valid."
            )
        
        # Map detected format to MIME type and check against allowed list
        allowed_mime = getattr(settings, 'ALLOWED_IMAGE_MIME_TYPES',
                                ['image/jpeg', 'image/png', 'image/gif', 'image/webp'])
        detected_mime = PIL_MIME_MAP.get(detected_format.upper())
        
        if detected_mime is None:
            raise serializers.ValidationError(
                f"Format gambar '{detected_format}' tidak didukung."
            )
        
        if detected_mime not in allowed_mime:
            raise serializers.ValidationError(
                f"Tipe file '{detected_mime}' tidak diizinkan. "
                f"Tipe yang diizinkan: {', '.join(allowed_mime)}"
            )
            
    except serializers.ValidationError:
        raise
    except Exception as e:
        logger.warning('Image validation error: %s', str(e))
        raise serializers.ValidationError(
            "File yang diunggah bukan gambar yang valid atau file rusak."
        )

    return value
