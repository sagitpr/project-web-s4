"""
Store image utilities for Warungio Marketplace.
Handles image resize, optimization, and format conversion.
"""

import logging
import io
import os
from django.core.files.base import ContentFile
from django.conf import settings

logger = logging.getLogger(__name__)

# ── Size Constraints ──
LOGO_MAX_SIZE = (400, 400)       # square-ish, max 400×400
BANNER_MAX_SIZE = (1200, 400)    # wide banner, max 1200×400

JPEG_QUALITY = 85               # Very good quality, ~60-80% size savings
PNG_QUALITY = 85                # Lossy PNG compression from Pillow
WEBP_QUALITY = 80               # Excellent compression, good quality


def resize_store_image(image_field, max_size=LOGO_MAX_SIZE, field_name='store_logo'):
    """
    Resize and optimize a store image (logo or banner) using Pillow.
    
    - Reads the uploaded image via Pillow.
    - Downsizes to fit within `max_size` while preserving aspect ratio.
    - Does NOT upscale (only makes images smaller).
    - Optimizes JPEG/PNG quality.
    
    Call this from Store.save() when the image has changed.
    
    Args:
        image_field: The ImageFieldFile (e.g., instance.store_logo).
        max_size: Tuple of (max_width, max_height).
        field_name: Human-readable name for logging.
    
    Returns:
        True if image was resized, False otherwise.
    """
    if not image_field or not image_field.name:
        return False

    try:
        from PIL import Image as PILImage
        
        # Open the stored file via Pillow
        img = PILImage.open(image_field.path)
        
        original_size = img.size
        original_format = img.format  # 'JPEG', 'PNG', 'GIF', 'WEBP', 'BMP'
        original_bytes = os.path.getsize(image_field.path) if os.path.exists(image_field.path) else 0
        
        # Determine output format — always keep original format to avoid
        # DB filename extension mismatch (the model field name isn't persisted
        # after resize with save=False)
        output_format = original_format
        
        # Convert RGBA/PA to RGB for JPEG output
        if output_format == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
            bg = PILImage.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = bg
        elif img.mode == 'P':
            img = img.convert('RGB') if output_format == 'JPEG' else img.convert('RGBA')
        
        # Resize: only downscale, never upscale
        img.thumbnail(max_size, PILImage.LANCZOS)
        
        # If the image was actually resized or needs re-encoding
        if img.size != original_size or original_format in ('BMP', 'TIFF'):
            # Save to a temporary buffer
            buf = io.BytesIO()
            
            save_kwargs = {'format': output_format}
            if output_format == 'JPEG':
                save_kwargs['quality'] = JPEG_QUALITY
                save_kwargs['optimize'] = True
            elif output_format == 'PNG':
                save_kwargs['compress_level'] = 6  # Default: good speed/size
            elif output_format == 'WEBP':
                save_kwargs['quality'] = WEBP_QUALITY
            
            img.save(buf, **save_kwargs)
            buf.seek(0)
            
            new_bytes = buf.tell()
            
            # Only replace if significantly smaller (>10% savings)
            if new_bytes < original_bytes * 0.9 or img.size != original_size:
                # Build the new filename
                old_path = image_field.path
                ext_map = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}
                new_ext = ext_map.get(output_format, '.jpg')
                
                # Preserve the original filename stem
                stem = os.path.splitext(os.path.basename(old_path))[0]
                new_filename = f"{stem}{new_ext}"
                
                # Save via the ImageField's save method (handles storage)
                image_field.save(new_filename, ContentFile(buf.read()), save=False)
                
                logger.info(
                    f"{field_name}: {original_size} → {img.size} | "
                    f"{original_bytes / 1024:.1f}KB → {new_bytes / 1024:.1f}KB | "
                    f"format={output_format}"
                )
                return True
        
        return False
    
    except Exception as e:
        logger.warning(f"Failed to resize {field_name}: {e}")
        return False
