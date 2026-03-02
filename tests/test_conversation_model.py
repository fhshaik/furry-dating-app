"""Tests for the Conversation SQLAlchemy model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestConversationImport:
    def test_conversation_is_importable(self):
        from app.models.conversation import Conversation

        assert Conversation is not None

    def test_conversation_type_is_importable(self):
        from app.models.conversation import ConversationType

        assert ConversationType is not None


class TestConversationTableName:
    def test_tablename_is_conversations(self):
        from app.models.conversation import Conversation

        assert Conversation.__tablename__ == "conversations"


class TestConversationColumns:
    def test_has_id_column(self):
        from app.models.conversation import Conversation

        assert hasattr(Conversation, "id")

    def test_has_type_column(self):
        from app.models.conversation import Conversation

        assert hasattr(Conversation, "type")

    def test_has_pack_id_column(self):
        from app.models.conversation import Conversation

        assert hasattr(Conversation, "pack_id")

    def test_has_created_at_column(self):
        from app.models.conversation import Conversation

        assert hasattr(Conversation, "created_at")


class TestConversationColumnTypes:
    def _get_col(self, model, col_name):
        return model.__table__.c[col_name]

    def test_id_is_integer_primary_key(self):
        from sqlalchemy import Integer

        from app.models.conversation import Conversation

        col = self._get_col(Conversation, "id")
        assert isinstance(col.type, Integer)
        assert col.primary_key

    def test_type_is_not_nullable(self):
        from app.models.conversation import Conversation

        col = self._get_col(Conversation, "type")
        assert not col.nullable

    def test_pack_id_is_integer_nullable(self):
        from sqlalchemy import Integer

        from app.models.conversation import Conversation

        col = self._get_col(Conversation, "pack_id")
        assert isinstance(col.type, Integer)
        assert col.nullable

    def test_created_at_is_datetime_not_nullable(self):
        from sqlalchemy import DateTime

        from app.models.conversation import Conversation

        col = self._get_col(Conversation, "created_at")
        assert isinstance(col.type, DateTime)
        assert not col.nullable


class TestConversationTypeEnum:
    def test_direct_value(self):
        from app.models.conversation import ConversationType

        assert ConversationType.DIRECT == "direct"

    def test_pack_value(self):
        from app.models.conversation import ConversationType

        assert ConversationType.PACK == "pack"


class TestConversationDefaults:
    def test_created_at_has_server_default(self):
        from app.models.conversation import Conversation

        col = Conversation.__table__.c["created_at"]
        assert col.server_default is not None


class TestConversationForeignKeys:
    def test_pack_id_has_foreign_key_to_packs(self):
        from app.models.conversation import Conversation

        col = Conversation.__table__.c["pack_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "packs.id" in fk_targets

    def test_pack_id_foreign_key_cascades_on_delete(self):
        from app.models.conversation import Conversation

        fks = Conversation.__table__.c["pack_id"].foreign_keys
        assert next(iter(fks)).ondelete == "CASCADE"


class TestConversationInstantiation:
    def test_can_instantiate_direct_conversation(self):
        from app.models.conversation import Conversation, ConversationType

        conv = Conversation(type=ConversationType.DIRECT)

        assert conv.type == ConversationType.DIRECT
        assert conv.pack_id is None

    def test_can_instantiate_pack_conversation(self):
        from app.models.conversation import Conversation, ConversationType

        conv = Conversation(type=ConversationType.PACK, pack_id=42)

        assert conv.type == ConversationType.PACK
        assert conv.pack_id == 42


class TestConversationInBase:
    def test_conversation_table_registered_in_metadata(self):
        from app.database import Base
        from app.models.conversation import Conversation  # noqa: F401 - ensures registration

        assert "conversations" in Base.metadata.tables
