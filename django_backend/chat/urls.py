"""
Chat URL configuration for Warungio Marketplace.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('conversations/', views.ConversationListView.as_view(), name='conversation-list'),
    path('conversations/create/', views.ConversationCreateView.as_view(), name='conversation-create'),
    path('conversations/start/', views.StartConversationView.as_view(), name='start-conversation'),
    path('conversations/<int:pk>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:conversation_id>/messages/', views.MessageListView.as_view(), name='message-list'),
    path('messages/send/', views.MessageCreateView.as_view(), name='message-send'),
    path('unread-count/', views.UnreadCountView.as_view(), name='chat-unread-count'),
]
