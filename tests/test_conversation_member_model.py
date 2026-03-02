"""Tests for the ConversationMember SQLAlchemy model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestConversationMemberImport:
    def test_conversation_member_is_importable(self):
        from app.models.conversation_member import ConversationMember

        assert ConversationMember is not None


class TestConversationMemberTableName:
    def test_tablename_is_conversation_members(self):
        from app.models.conversation_member import ConversationMember

        assert ConversationMember.__tablename__ == "conversation_members"


class TestConversationMemberColumns:
    def test_has_conversation_id_column(self):
        from app.models.conversation_member import ConversationMember

        assert hasattr(ConversationMember, "conversation_id")

    def test_has_user_id_column(self):
        from app.models.conversation_member import ConversationMember

        assert hasattr(ConversationMember, "user_id")


class TestConversationMemberColumnTypes:
    def _get_col(self, model, col_name):
        return model.__table__.c[col_name]

    def test_conversation_id_is_integer_primary_key(self):
        from sqlalchemy import Integer

        from app.models.conversation_member import ConversationMember

        col = self._get_col(ConversationMember, "conversation_id")
        assert isinstance(col.type, Integer)
        assert col.primary_key
        assert not col.nullable

    def test_user_id_is_integer_primary_key(self):
        from sqlalchemy import Integer

        from app.models.conversation_member import ConversationMember

        col = self._get_col(ConversationMember, "user_id")
        assert isinstance(col.type, Integer)
        assert col.primary_key
        assert not col.nullable


class TestConversationMemberForeignKeys:
    def test_conversation_id_has_foreign_key_to_conversations(self):
        from app.models.conversation_member import ConversationMember

        col = ConversationMember.__table__.c["conversation_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "conversations.id" in fk_targets

    def test_user_id_has_foreign_key_to_users(self):
        from app.models.conversation_member import ConversationMember

        col = ConversationMember.__table__.c["user_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "users.id" in fk_targets

    def test_foreign_keys_cascade_on_delete(self):
        from app.models.conversation_member import ConversationMember

        conv_fks = ConversationMember.__table__.c["conversation_id"].foreign_keys
        user_fks = ConversationMember.__table__.c["user_id"].foreign_keys

        assert next(iter(conv_fks)).ondelete == "CASCADE"
        assert next(iter(user_fks)).ondelete == "CASCADE"


class TestConversationMemberInstantiation:
    def test_can_instantiate_with_required_fields(self):
        from app.models.conversation_member import ConversationMember

        member = ConversationMember(conversation_id=1, user_id=2)

        assert member.conversation_id == 1
        assert member.user_id == 2


class TestConversationMemberInBase:
    def test_conversation_member_table_registered_in_metadata(self):
        from app.database import Base
        from app.models.conversation_member import ConversationMember  # noqa: F401

        assert "conversation_members" in Base.metadata.tables
