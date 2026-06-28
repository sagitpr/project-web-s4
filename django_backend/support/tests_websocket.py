"""
Async WebSocket consumer tests for SupportChatConsumer.
Run with: pytest support/tests_websocket.py -v
"""
import asyncio
import pytest

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def support_chat_user():
    """Create a test user for authenticated WebSocket chat tests."""
    from accounts.models import User
    user = User.objects.create_user(
        username='wsuser', email='ws@test.com',
        password='Test123!', full_name='WS Test User',
    )
    return user


@pytest.fixture
def support_chat_communicator_factory():
    """Return a factory function that creates a configured WebsocketCommunicator."""
    from channels.testing import WebsocketCommunicator
    from channels.auth import AuthMiddlewareStack
    from channels.routing import URLRouter
    from support.routing import websocket_urlpatterns

    def _make(user=None):
        application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        comm = WebsocketCommunicator(application, '/ws/support/chat/')
        if user:
            comm.scope['user'] = user
        return comm

    return _make


@pytest.mark.asyncio
async def test_connect_sends_welcome(support_chat_communicator_factory, channels_settings):
    """Connect should send a welcome system message."""
    comm = support_chat_communicator_factory()
    connected, _ = await comm.connect()
    assert connected is True

    response = await comm.receive_json_from(timeout=5)
    assert response['type'] == 'system'
    assert 'Terhubung' in response['content']

    await comm.disconnect()


@pytest.mark.asyncio
async def test_connect_anonymous_allowed(support_chat_communicator_factory, channels_settings):
    """Anonymous users should be able to connect to support chat."""
    comm = support_chat_communicator_factory()
    connected, _ = await comm.connect()
    assert connected is True
    await comm.disconnect()


@pytest.mark.asyncio
async def test_send_message_authenticated(
    support_chat_user, support_chat_communicator_factory, channels_settings
):
    """Authenticated users can send messages and receive them back."""
    comm = support_chat_communicator_factory(user=support_chat_user)
    await comm.connect()
    await comm.receive_json_from(timeout=5)  # Consume welcome

    await comm.send_json_to({'type': 'message', 'content': 'Halo admin!'})
    response = await comm.receive_json_from(timeout=5)

    assert response['type'] == 'message'
    assert response['message']['content'] == 'Halo admin!'
    assert response['sender_name'] == 'WS Test User'

    await comm.disconnect()


@pytest.mark.asyncio
async def test_send_message_anonymous(support_chat_communicator_factory, channels_settings):
    """Anonymous users can send messages and receive them back."""
    comm = support_chat_communicator_factory()
    await comm.connect()
    await comm.receive_json_from(timeout=5)  # Consume welcome

    await comm.send_json_to({'type': 'message', 'content': 'Saya guest!'})
    response = await comm.receive_json_from(timeout=5)

    assert response['type'] == 'message'
    assert response['sender_name'] == 'Anda'

    await comm.disconnect()


@pytest.mark.asyncio
async def test_empty_message_ignored(support_chat_communicator_factory, channels_settings):
    """Empty/whitespace-only messages should not produce a response.

    Sends an empty message followed by a valid one, verifying only
    the valid message produces output.
    """
    comm = support_chat_communicator_factory()
    await comm.connect()
    await comm.receive_json_from(timeout=5)  # Consume welcome

    # Send empty message (should be ignored with no response)
    await comm.send_json_to({'type': 'message', 'content': '   '})

    # Send a valid message right after
    await comm.send_json_to({'type': 'message', 'content': 'Valid message!'})

    # Should receive only ONE response (for the valid message)
    response = await comm.receive_json_from(timeout=5)
    assert response['type'] == 'message'
    assert response['message']['content'] == 'Valid message!'

    await comm.disconnect()


@pytest.mark.asyncio
async def test_typing_indicator(support_chat_communicator_factory, channels_settings):
    """Typing indicator events echo back correctly."""
    comm = support_chat_communicator_factory()
    await comm.connect()
    await comm.receive_json_from(timeout=5)  # Consume welcome

    await comm.send_json_to({'type': 'typing', 'is_typing': True})
    response = await comm.receive_json_from(timeout=5)

    assert response['type'] == 'typing'
    assert response['is_typing'] is True

    await comm.disconnect()


@pytest.mark.asyncio
async def test_disconnect_cleanup(support_chat_communicator_factory, channels_settings):
    """Disconnect should not raise any errors."""
    comm = support_chat_communicator_factory()
    await comm.connect()
    await comm.receive_json_from(timeout=5)  # Consume welcome
    await comm.disconnect()  # No error expected
