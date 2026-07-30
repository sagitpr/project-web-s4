"""
Centralized contact configuration for Warungio.
SINGLE SOURCE OF TRUTH for all official contact information.

All templates, views, serializers, and JavaScript must reference
these constants — NEVER hardcode contact info elsewhere.
"""

# ── Official Warungio Contact Information ──
COMPANY_NAME = "Warungio"
COMPANY_SLOGAN = "Ekosistem Marketplace Hyperlocal & Manajemen Bisnis UMKM"

# Official Address
ADDRESS_STREET = "Jl. Nasional III No.17"
ADDRESS_VILLAGE = "Manggungsari"
ADDRESS_DISTRICT = "Rajapolah"
ADDRESS_CITY = "Tasikmalaya"
ADDRESS_PROVINCE = "Jawa Barat"
ADDRESS_POSTAL_CODE = "46155"
ADDRESS_COUNTRY = "Indonesia"

FULL_ADDRESS = (
    f"{ADDRESS_STREET}, {ADDRESS_VILLAGE}, "
    f"Kec. {ADDRESS_DISTRICT}, "
    f"Kab. {ADDRESS_CITY}, "
    f"{ADDRESS_PROVINCE} {ADDRESS_POSTAL_CODE}"
)

# Official Phone / WhatsApp
PHONE_NUMBER = "+6287833847895"
WHATSAPP_NUMBER = "6287833847895"  # Without + for wa.me links
WHATSAPP_DISPLAY = "+62 878-3384-7895"
PHONE_DISPLAY = "(0265) 123456"

# Official Email
EMAIL_CONTACT = "warungio.id@gmail.com"
EMAIL_SUPPORT = "warungio.id@gmail.com"
EMAIL_INFO = "warungio.id@gmail.com"

# Google Maps (if you have a Maps URL)
GOOGLE_MAPS_URL = (
    "https://maps.google.com/?q="
    "Jl.+Nasional+III+No.17,+Manggungsari,"
    "+Rajapolah,+Tasikmalaya,+Jawa+Barat+46155"
)

# Social Media
SOCIAL_MEDIA = {
    "facebook": "https://facebook.com/warungio",
    "instagram": "https://instagram.com/warungio",
    "twitter": "https://twitter.com/warungio",
    "youtube": "https://youtube.com/@warungio",
    "whatsapp": f"https://wa.me/{WHATSAPP_NUMBER}",
}

def get_whatsapp_url(text=None):
    """Generate WhatsApp URL with optional pre-filled message."""
    url = f"https://wa.me/{WHATSAPP_NUMBER}"
    if text:
        from urllib.parse import quote
        url += f"?text={quote(text)}"
    return url
