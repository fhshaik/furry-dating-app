"""Tests for the PackMember SQLAlchemy model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestPackMemberImport:
    def test_pack_member_is_importable(self):
        from app.models.pack_member import PackMember, PackMemberRole

        assert PackMember is not None
        assert PackMemberRole is not None


class TestPackMemberTableName:
    def test_tablename_is_pack_members(self):
        from app.models.pack_member import PackMember

        assert PackMember.__tablename__ == "pack_members"


class TestPackMemberColumns:
    def test_has_pack_id_column(self):
        from app.models.pack_member import PackMember

        assert hasattr(PackMember, "pack_id")

    def test_has_user_id_column(self):
        from app.models.pack_member import PackMember

        assert hasattr(PackMember, "user_id")

    def test_has_role_column(self):
        from app.models.pack_member import PackMember

        assert hasattr(PackMember, "role")

    def test_has_joined_at_column(self):
        from app.models.pack_member import PackMember

        assert hasattr(PackMember, "joined_at")


class TestPackMemberColumnTypes:
    def _get_col(self, model, col_name):
        return model.__table__.c[col_name]

    def test_pack_id_is_integer_primary_key(self):
        from sqlalchemy import Integer

        from app.models.pack_member import PackMember

        col = self._get_col(PackMember, "pack_id")
        assert isinstance(col.type, Integer)
        assert col.primary_key
        assert not col.nullable

    def test_user_id_is_integer_primary_key(self):
        from sqlalchemy import Integer

        from app.models.pack_member import PackMember

        col = self._get_col(PackMember, "user_id")
        assert isinstance(col.type, Integer)
        assert col.primary_key
        assert not col.nullable

    def test_role_is_enum_not_nullable(self):
        from sqlalchemy import Enum

        from app.models.pack_member import PackMember

        col = self._get_col(PackMember, "role")
        assert isinstance(col.type, Enum)
        assert not col.nullable
        assert tuple(col.type.enums) == ("admin", "member")

    def test_joined_at_is_datetime_not_nullable(self):
        from sqlalchemy import DateTime

        from app.models.pack_member import PackMember

        col = self._get_col(PackMember, "joined_at")
        assert isinstance(col.type, DateTime)
        assert not col.nullable


class TestPackMemberDefaults:
    def test_role_has_server_default_member(self):
        from app.models.pack_member import PackMember

        col = PackMember.__table__.c["role"]
        assert col.server_default is not None
        assert col.server_default.arg == "member"

    def test_joined_at_has_server_default(self):
        from app.models.pack_member import PackMember

        col = PackMember.__table__.c["joined_at"]
        assert col.server_default is not None


class TestPackMemberForeignKeys:
    def test_pack_id_has_foreign_key_to_packs(self):
        from app.models.pack_member import PackMember

        col = PackMember.__table__.c["pack_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "packs.id" in fk_targets

    def test_user_id_has_foreign_key_to_users(self):
        from app.models.pack_member import PackMember

        col = PackMember.__table__.c["user_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "users.id" in fk_targets

    def test_foreign_keys_cascade_on_delete(self):
        from app.models.pack_member import PackMember

        pack_fks = PackMember.__table__.c["pack_id"].foreign_keys
        user_fks = PackMember.__table__.c["user_id"].foreign_keys

        assert next(iter(pack_fks)).ondelete == "CASCADE"
        assert next(iter(user_fks)).ondelete == "CASCADE"


class TestPackMemberInstantiation:
    def test_can_instantiate_with_required_fields(self):
        from app.models.pack_member import PackMember

        pack_member = PackMember(pack_id=1, user_id=2)

        assert pack_member.pack_id == 1
        assert pack_member.user_id == 2

    def test_can_set_admin_role(self):
        from app.models.pack_member import PackMember, PackMemberRole

        pack_member = PackMember(pack_id=1, user_id=2, role=PackMemberRole.ADMIN)

        assert pack_member.role == PackMemberRole.ADMIN


class TestPackMemberInBase:
    def test_pack_member_table_registered_in_metadata(self):
        from app.database import Base
        from app.models.pack_member import PackMember  # noqa: F401 - ensures registration

        assert "pack_members" in Base.metadata.tables
