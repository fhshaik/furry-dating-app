"""Tests for the PackJoinRequest SQLAlchemy model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestPackJoinRequestImport:
    def test_pack_join_request_is_importable(self):
        from app.models.pack_join_request import PackJoinRequest, PackJoinRequestStatus

        assert PackJoinRequest is not None
        assert PackJoinRequestStatus is not None


class TestPackJoinRequestTableName:
    def test_tablename_is_pack_join_requests(self):
        from app.models.pack_join_request import PackJoinRequest

        assert PackJoinRequest.__tablename__ == "pack_join_requests"


class TestPackJoinRequestColumns:
    def test_has_id_column(self):
        from app.models.pack_join_request import PackJoinRequest

        assert hasattr(PackJoinRequest, "id")

    def test_has_pack_id_column(self):
        from app.models.pack_join_request import PackJoinRequest

        assert hasattr(PackJoinRequest, "pack_id")

    def test_has_user_id_column(self):
        from app.models.pack_join_request import PackJoinRequest

        assert hasattr(PackJoinRequest, "user_id")

    def test_has_status_column(self):
        from app.models.pack_join_request import PackJoinRequest

        assert hasattr(PackJoinRequest, "status")

    def test_has_created_at_column(self):
        from app.models.pack_join_request import PackJoinRequest

        assert hasattr(PackJoinRequest, "created_at")


class TestPackJoinRequestColumnTypes:
    def _get_col(self, model, col_name):
        return model.__table__.c[col_name]

    def test_id_is_integer_primary_key(self):
        from sqlalchemy import Integer

        from app.models.pack_join_request import PackJoinRequest

        col = self._get_col(PackJoinRequest, "id")
        assert isinstance(col.type, Integer)
        assert col.primary_key

    def test_pack_id_is_integer_not_nullable(self):
        from sqlalchemy import Integer

        from app.models.pack_join_request import PackJoinRequest

        col = self._get_col(PackJoinRequest, "pack_id")
        assert isinstance(col.type, Integer)
        assert not col.nullable

    def test_user_id_is_integer_not_nullable(self):
        from sqlalchemy import Integer

        from app.models.pack_join_request import PackJoinRequest

        col = self._get_col(PackJoinRequest, "user_id")
        assert isinstance(col.type, Integer)
        assert not col.nullable

    def test_status_is_named_enum_not_nullable(self):
        from sqlalchemy import Enum

        from app.models.pack_join_request import PackJoinRequest

        col = self._get_col(PackJoinRequest, "status")
        assert isinstance(col.type, Enum)
        assert col.type.name == "join_request_status"
        assert tuple(col.type.enums) == ("pending", "approved", "denied")
        assert not col.nullable

    def test_created_at_is_datetime_not_nullable(self):
        from sqlalchemy import DateTime

        from app.models.pack_join_request import PackJoinRequest

        col = self._get_col(PackJoinRequest, "created_at")
        assert isinstance(col.type, DateTime)
        assert not col.nullable


class TestPackJoinRequestDefaults:
    def test_status_has_server_default_pending(self):
        from app.models.pack_join_request import PackJoinRequest

        col = PackJoinRequest.__table__.c["status"]
        assert col.server_default is not None
        assert col.server_default.arg == "pending"

    def test_created_at_has_server_default(self):
        from app.models.pack_join_request import PackJoinRequest

        col = PackJoinRequest.__table__.c["created_at"]
        assert col.server_default is not None


class TestPackJoinRequestForeignKeys:
    def test_pack_id_has_foreign_key_to_packs(self):
        from app.models.pack_join_request import PackJoinRequest

        col = PackJoinRequest.__table__.c["pack_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "packs.id" in fk_targets

    def test_user_id_has_foreign_key_to_users(self):
        from app.models.pack_join_request import PackJoinRequest

        col = PackJoinRequest.__table__.c["user_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "users.id" in fk_targets

    def test_foreign_keys_cascade_on_delete(self):
        from app.models.pack_join_request import PackJoinRequest

        pack_fks = PackJoinRequest.__table__.c["pack_id"].foreign_keys
        user_fks = PackJoinRequest.__table__.c["user_id"].foreign_keys

        assert next(iter(pack_fks)).ondelete == "CASCADE"
        assert next(iter(user_fks)).ondelete == "CASCADE"


class TestPackJoinRequestInstantiation:
    def test_can_instantiate_with_required_fields(self):
        from app.models.pack_join_request import PackJoinRequest

        pack_join_request = PackJoinRequest(pack_id=1, user_id=2)

        assert pack_join_request.pack_id == 1
        assert pack_join_request.user_id == 2

    def test_can_set_denied_status(self):
        from app.models.pack_join_request import PackJoinRequest, PackJoinRequestStatus

        pack_join_request = PackJoinRequest(
            pack_id=1,
            user_id=2,
            status=PackJoinRequestStatus.DENIED,
        )

        assert pack_join_request.status == PackJoinRequestStatus.DENIED


class TestPackJoinRequestEnum:
    def test_status_values_match_schema(self):
        from app.models.pack_join_request import PackJoinRequestStatus

        assert PackJoinRequestStatus.PENDING.value == "pending"
        assert PackJoinRequestStatus.APPROVED.value == "approved"
        assert PackJoinRequestStatus.DENIED.value == "denied"


class TestPackJoinRequestInBase:
    def test_pack_join_request_table_registered_in_metadata(self):
        from app.database import Base
        from app.models.pack_join_request import PackJoinRequest  # noqa: F401

        assert "pack_join_requests" in Base.metadata.tables
