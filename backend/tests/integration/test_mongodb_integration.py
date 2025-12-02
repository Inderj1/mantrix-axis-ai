"""
Integration tests for MongoDBClient with real MongoDB.

These tests require MongoDB to be running on localhost:27017.
Run with: pytest tests/integration/test_mongodb_integration.py -v
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List
import uuid


# Skip all tests if MongoDB is not available
pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="module")]


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def mongodb_client():
    """Create a real MongoDBClient connected to MongoDB."""
    from src.db.mongodb_client import MongoDBClient
    from src.config import settings

    # Store original settings
    original_url = settings.mongodb_url
    original_db = settings.mongodb_database

    # Use test database
    settings.mongodb_url = "mongodb://localhost:27017"
    settings.mongodb_database = "test_nlp_sql_conversations"

    client = None
    try:
        client = MongoDBClient()
        await client.connect()
        yield client
    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")
    finally:
        # Cleanup
        if client and client.client:
            try:
                await client.client.drop_database("test_nlp_sql_conversations")
                await client.disconnect()
            except:
                pass
        settings.mongodb_url = original_url
        settings.mongodb_database = original_db


@pytest_asyncio.fixture(loop_scope="module")
async def clean_collections(mongodb_client):
    """Clean up test conversations before each test."""
    # Delete test conversations
    await mongodb_client.conversations_collection.delete_many({
        "conversationId": {"$regex": "^test_"}
    })
    yield
    # Clean up after test
    await mongodb_client.conversations_collection.delete_many({
        "conversationId": {"$regex": "^test_"}
    })


class TestMongoDBConnection:
    """Test MongoDB connection and basic operations."""

    async def test_client_connected(self, mongodb_client):
        """Test that client is connected."""
        assert mongodb_client.client is not None
        result = await mongodb_client.client.admin.command('ping')
        assert result.get('ok') == 1.0

    async def test_collections_exist(self, mongodb_client):
        """Test that required collections are accessible."""
        assert mongodb_client.conversations_collection is not None
        assert mongodb_client.dashboards_collection is not None


class TestConversationCRUD:
    """Test conversation CRUD operations."""

    async def test_create_conversation(self, mongodb_client, clean_collections):
        """Test creating a new conversation."""
        conversation_id = f"test_{uuid.uuid4().hex[:8]}"

        conversation = await mongodb_client.create_conversation(
            conversation_id=conversation_id,
            user_id="test_user"
        )

        assert conversation is not None
        assert conversation["conversationId"] == conversation_id
        assert conversation["userId"] == "test_user"
        assert conversation["title"] == "New Conversation"
        assert conversation["messages"] == []

    async def test_get_conversation(self, mongodb_client, clean_collections):
        """Test retrieving a conversation."""
        conversation_id = f"test_{uuid.uuid4().hex[:8]}"

        # Create a conversation
        await mongodb_client.create_conversation(
            conversation_id=conversation_id,
            user_id="test_user"
        )

        # Retrieve it
        conversation = await mongodb_client.get_conversation(conversation_id)

        assert conversation is not None
        assert conversation["conversationId"] == conversation_id

    async def test_get_nonexistent_conversation(self, mongodb_client, clean_collections):
        """Test retrieving a non-existent conversation."""
        conversation = await mongodb_client.get_conversation("nonexistent_id_xyz123")
        assert conversation is None

    async def test_list_conversations(self, mongodb_client, clean_collections):
        """Test listing conversations for a user."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        # Create multiple conversations
        for i in range(5):
            await mongodb_client.create_conversation(
                conversation_id=f"test_conv_{i}_{uuid.uuid4().hex[:8]}",
                user_id=user_id
            )

        # List conversations
        conversations = await mongodb_client.list_conversations(
            user_id=user_id,
            limit=10
        )

        assert len(conversations) == 5

    async def test_delete_conversation(self, mongodb_client, clean_collections):
        """Test deleting a conversation."""
        conversation_id = f"test_{uuid.uuid4().hex[:8]}"

        # Create a conversation
        await mongodb_client.create_conversation(
            conversation_id=conversation_id,
            user_id="test_user"
        )

        # Verify it exists
        conversation = await mongodb_client.get_conversation(conversation_id)
        assert conversation is not None

        # Delete it
        deleted = await mongodb_client.delete_conversation(conversation_id)
        assert deleted is True

        # Verify it's gone
        conversation = await mongodb_client.get_conversation(conversation_id)
        assert conversation is None


class TestConversationMessages:
    """Test conversation message operations."""

    async def test_add_user_message(self, mongodb_client, clean_collections):
        """Test adding a user message."""
        conversation_id = f"test_{uuid.uuid4().hex[:8]}"

        # Create a conversation
        await mongodb_client.create_conversation(
            conversation_id=conversation_id,
            user_id="test_user"
        )

        # Add a message
        message = {
            "type": "user",
            "content": "What are the total sales for Q4?",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        result = await mongodb_client.add_message(conversation_id, message)
        assert result is True

        # Verify the message was added
        conversation = await mongodb_client.get_conversation(conversation_id)
        assert len(conversation["messages"]) == 1
        assert conversation["messages"][0]["content"] == "What are the total sales for Q4?"

    async def test_add_assistant_message(self, mongodb_client, clean_collections):
        """Test adding an assistant response."""
        conversation_id = f"test_{uuid.uuid4().hex[:8]}"

        # Create a conversation
        await mongodb_client.create_conversation(
            conversation_id=conversation_id,
            user_id="test_user"
        )

        # Add user message first
        user_message = {
            "type": "user",
            "content": "Show me customer data",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await mongodb_client.add_message(conversation_id, user_message)

        # Add assistant response
        assistant_message = {
            "type": "assistant",
            "content": "Here's the SQL for customer data: SELECT * FROM customers",
            "sql": "SELECT * FROM customers",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await mongodb_client.add_message(conversation_id, assistant_message)

        # Verify both messages exist
        conversation = await mongodb_client.get_conversation(conversation_id)
        assert len(conversation["messages"]) == 2
        assert conversation["messages"][1]["type"] == "assistant"

    async def test_first_user_message_updates_title(self, mongodb_client, clean_collections):
        """Test that the first user message updates the conversation title."""
        conversation_id = f"test_{uuid.uuid4().hex[:8]}"

        # Create a conversation
        await mongodb_client.create_conversation(
            conversation_id=conversation_id,
            user_id="test_user"
        )

        # Add first user message
        message = {
            "type": "user",
            "content": "Show me the revenue trends for the past year",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await mongodb_client.add_message(conversation_id, message)

        # Verify title was updated
        conversation = await mongodb_client.get_conversation(conversation_id)
        assert "revenue trends" in conversation["title"].lower()


class TestConversationUpdates:
    """Test conversation update operations."""

    async def test_update_conversation_title(self, mongodb_client, clean_collections):
        """Test updating conversation title."""
        conversation_id = f"test_{uuid.uuid4().hex[:8]}"

        # Create a conversation
        await mongodb_client.create_conversation(
            conversation_id=conversation_id,
            user_id="test_user"
        )

        # Update title
        updated = await mongodb_client.update_conversation(
            conversation_id=conversation_id,
            updates={"title": "Revenue Analysis Q4 2024"}
        )
        assert updated is True

        # Verify update
        conversation = await mongodb_client.get_conversation(conversation_id)
        assert conversation["title"] == "Revenue Analysis Q4 2024"

    async def test_update_conversation_metadata(self, mongodb_client, clean_collections):
        """Test updating conversation metadata."""
        conversation_id = f"test_{uuid.uuid4().hex[:8]}"

        # Create a conversation
        await mongodb_client.create_conversation(
            conversation_id=conversation_id,
            user_id="test_user"
        )

        # Update metadata
        updated = await mongodb_client.update_conversation(
            conversation_id=conversation_id,
            updates={
                "metadata.starred": True,
                "metadata.tags": ["finance", "quarterly"]
            }
        )
        assert updated is True

        # Verify update
        conversation = await mongodb_client.get_conversation(conversation_id)
        assert conversation["metadata"]["starred"] is True
        assert "finance" in conversation["metadata"]["tags"]


class TestConversationPagination:
    """Test conversation pagination."""

    async def test_list_with_limit(self, mongodb_client, clean_collections):
        """Test listing with limit."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        # Create 10 conversations
        for i in range(10):
            await mongodb_client.create_conversation(
                conversation_id=f"test_conv_{i}_{uuid.uuid4().hex[:8]}",
                user_id=user_id
            )

        # Get only 5
        conversations = await mongodb_client.list_conversations(
            user_id=user_id,
            limit=5
        )

        assert len(conversations) == 5

    async def test_list_with_skip(self, mongodb_client, clean_collections):
        """Test listing with skip (pagination)."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        # Create 10 conversations
        for i in range(10):
            await mongodb_client.create_conversation(
                conversation_id=f"test_conv_{i}_{uuid.uuid4().hex[:8]}",
                user_id=user_id
            )

        # Get page 2 (skip 5, limit 5)
        page1 = await mongodb_client.list_conversations(
            user_id=user_id,
            limit=5,
            skip=0
        )
        page2 = await mongodb_client.list_conversations(
            user_id=user_id,
            limit=5,
            skip=5
        )

        assert len(page1) == 5
        assert len(page2) == 5

        # Ensure no overlap
        page1_ids = set(c["conversationId"] for c in page1)
        page2_ids = set(c["conversationId"] for c in page2)
        assert len(page1_ids & page2_ids) == 0


class TestConversationIsolation:
    """Test user conversation isolation."""

    async def test_users_see_only_their_conversations(self, mongodb_client, clean_collections):
        """Test that users only see their own conversations."""
        user1_id = f"test_user1_{uuid.uuid4().hex[:8]}"
        user2_id = f"test_user2_{uuid.uuid4().hex[:8]}"

        # Create conversations for user 1
        for i in range(3):
            await mongodb_client.create_conversation(
                conversation_id=f"test_user1_conv_{i}_{uuid.uuid4().hex[:8]}",
                user_id=user1_id
            )

        # Create conversations for user 2
        for i in range(5):
            await mongodb_client.create_conversation(
                conversation_id=f"test_user2_conv_{i}_{uuid.uuid4().hex[:8]}",
                user_id=user2_id
            )

        # User 1 should see 3 conversations
        user1_convs = await mongodb_client.list_conversations(user_id=user1_id)
        assert len(user1_convs) == 3

        # User 2 should see 5 conversations
        user2_convs = await mongodb_client.list_conversations(user_id=user2_id)
        assert len(user2_convs) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
