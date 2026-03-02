"""Tests for the Message SQLAlchemy model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestMessageImport:
    def test_message_is_importable(self):
        from app.models.message import Message

        assert Message is not None


class TestMessageTableName:
    def test_tablename_is_messages(self):
        from app.models.message import Message

        assert Message.__tablename__ == "messages"


class TestMessageColumns:
    def test_has_id_column(self):
        from app.models.message import Message

        assert hasattr(Message, "id")

    def test_has_conversation_id_column(self):
        from app.models.message import Message

        assert hasattr(Message, "conversation_id")

    def test_has_sender_id_column(self):
        from app.models.message import Message

        assert hasattr(Message, "sender_id")

    def test_has_content_column(self):
        from app.models.message import Message

        assert hasattr(Message, "content")

    def test_has_sent_at_column(self):
        from app.models.message import Message

        assert hasattr(Message, "sent_at")

    def test_has_is_read_column(self):
        from app.models.message import Message

        assert hasattr(Message, "is_read")


class TestMessageColumnTypes:
    def _get_col(self, model, col_name):
        return model.__table__.c[col_name]

    def test_id_is_integer_primary_key(self):
        from sqlalchemy import Integer

        from app.models.message import Message

        col = self._get_col(Message, "id")
        assert isinstance(col.type, Integer)
        assert col.primary_key

    def test_conversation_id_is_integer(self):
        from sqlalchemy import Integer

        from app.models.message import Message

        col = self._get_col(Message, "conversation_id")
        assert isinstance(col.type, Integer)
        assert not col.nullable

    def test_sender_id_is_integer(self):
        from sqlalchemy import Integer

        from app.models.message import Message

        col = self._get_col(Message, "sender_id")
        assert isinstance(col.type, Integer)
        assert not col.nullable

    def test_content_is_text(self):
        from sqlalchemy import Text

        from app.models.message import Message

        col = self._get_col(Message, "content")
        assert isinstance(col.type, Text)
        assert not col.nullable

    def test_sent_at_is_datetime(self):
        from sqlalchemy import DateTime

        from app.models.message import Message

        col = self._get_col(Message, "sent_at")
        assert isinstance(col.type, DateTime)
        assert not col.nullable

    def test_is_read_is_boolean(self):
        from sqlalchemy import Boolean

        from app.models.message import Message

        col = self._get_col(Message, "is_read")
        assert isinstance(col.type, Boolean)
        assert not col.nullable


class TestMessageForeignKeys:
    def test_conversation_id_has_foreign_key_to_conversations(self):
        from app.models.message import Message

        col = Message.__table__.c["conversation_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "conversations.id" in fk_targets

    def test_sender_id_has_foreign_key_to_users(self):
        from app.models.message import Message

        col = Message.__table__.c["sender_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "users.id" in fk_targets

    def test_foreign_keys_cascade_on_delete(self):
        from app.models.message import Message

        conv_fks = Message.__table__.c["conversation_id"].foreign_keys
        user_fks = Message.__table__.c["sender_id"].foreign_keys

        assert next(iter(conv_fks)).ondelete == "CASCADE"
        assert next(iter(user_fks)).ondelete == "CASCADE"


class TestMessageInstantiation:
    def test_can_instantiate_with_required_fields(self):
        from app.models.message import Message

        msg = Message(conversation_id=1, sender_id=2, content="Hello!")

        assert msg.conversation_id == 1
        assert msg.sender_id == 2
        assert msg.content == "Hello!"


class TestMessageInBase:
    def test_message_table_registered_in_metadata(self):
        from app.database import Base
        from app.models.message import Message  # noqa: F401

        assert "messages" in Base.metadata.tables
