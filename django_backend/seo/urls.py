"""SEO URL configuration - robots.txt and sitemap.xml."""

from django.urls import path
from . import views

urlpatterns = [
    path('robots.txt', views.robots_txt, name='robots-txt'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap-xml'),
]
