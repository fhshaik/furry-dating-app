"""Tests for the Swipe SQLAlchemy model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestSwipeImport:
    def test_swipe_is_importable(self):
        from app.models.swipe import Swipe

        assert Swipe is not None

    def test_swipe_action_is_importable(self):
        from app.models.swipe import SwipeAction

        assert SwipeAction is not None

    def test_swipe_importable_from_models_package(self):
        from app.models import Swipe

        assert Swipe is not None

    def test_swipe_in_models_all(self):
        import app.models as models

        assert "Swipe" in models.__all__
        assert "SwipeAction" in models.__all__


class TestSwipeTableName:
    def test_tablename_is_swipes(self):
        from app.models.swipe import Swipe

        assert Swipe.__tablename__ == "swipes"


class TestSwipeColumns:
    def test_has_id_column(self):
        from app.models.swipe import Swipe

        assert hasattr(Swipe, "id")

    def test_has_swiper_id_column(self):
        from app.models.swipe import Swipe

        assert hasattr(Swipe, "swiper_id")

    def test_has_target_user_id_column(self):
        from app.models.swipe import Swipe

        assert hasattr(Swipe, "target_user_id")

    def test_has_target_pack_id_column(self):
        from app.models.swipe import Swipe

        assert hasattr(Swipe, "target_pack_id")

    def test_has_action_column(self):
        from app.models.swipe import Swipe

        assert hasattr(Swipe, "action")

    def test_has_created_at_column(self):
        from app.models.swipe import Swipe

        assert hasattr(Swipe, "created_at")


class TestSwipeColumnTypes:
    def _get_col(self, model, col_name):
        return model.__table__.c[col_name]

    def test_id_is_integer_primary_key(self):
        from sqlalchemy import Integer

        from app.models.swipe import Swipe

        col = self._get_col(Swipe, "id")
        assert isinstance(col.type, Integer)
        assert col.primary_key

    def test_swiper_id_is_integer_not_nullable(self):
        from sqlalchemy import Integer

        from app.models.swipe import Swipe

        col = self._get_col(Swipe, "swiper_id")
        assert isinstance(col.type, Integer)
        assert not col.nullable

    def test_target_user_id_is_integer_nullable(self):
        from sqlalchemy import Integer

        from app.models.swipe import Swipe

        col = self._get_col(Swipe, "target_user_id")
        assert isinstance(col.type, Integer)
        assert col.nullable

    def test_target_pack_id_is_integer_nullable(self):
        from sqlalchemy import Integer

        from app.models.swipe import Swipe

        col = self._get_col(Swipe, "target_pack_id")
        assert isinstance(col.type, Integer)
        assert col.nullable

    def test_action_is_named_enum_not_nullable(self):
        from sqlalchemy import Enum

        from app.models.swipe import Swipe

        col = self._get_col(Swipe, "action")
        assert isinstance(col.type, Enum)
        assert col.type.name == "swipe_action"
        assert set(col.type.enums) == {"like", "pass"}
        assert not col.nullable

    def test_created_at_is_datetime_not_nullable(self):
        from sqlalchemy import DateTime

        from app.models.swipe import Swipe

        col = self._get_col(Swipe, "created_at")
        assert isinstance(col.type, DateTime)
        assert not col.nullable


class TestSwipeDefaults:
    def test_created_at_has_server_default(self):
        from app.models.swipe import Swipe

        col = Swipe.__table__.c["created_at"]
        assert col.server_default is not None


class TestSwipeForeignKeys:
    def test_swiper_id_has_foreign_key_to_users(self):
        from app.models.swipe import Swipe

        col = Swipe.__table__.c["swiper_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "users.id" in fk_targets

    def test_target_user_id_has_foreign_key_to_users(self):
        from app.models.swipe import Swipe

        col = Swipe.__table__.c["target_user_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "users.id" in fk_targets

    def test_target_pack_id_has_foreign_key_to_packs(self):
        from app.models.swipe import Swipe

        col = Swipe.__table__.c["target_pack_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "packs.id" in fk_targets

    def test_user_foreign_keys_cascade_on_delete(self):
        from app.models.swipe import Swipe

        swiper_fks = Swipe.__table__.c["swiper_id"].foreign_keys
        target_user_fks = Swipe.__table__.c["target_user_id"].foreign_keys

        assert next(iter(swiper_fks)).ondelete == "CASCADE"
        assert next(iter(target_user_fks)).ondelete == "CASCADE"

    def test_target_pack_foreign_key_cascades_on_delete(self):
        from app.models.swipe import Swipe

        pack_fks = Swipe.__table__.c["target_pack_id"].foreign_keys
        assert next(iter(pack_fks)).ondelete == "CASCADE"


class TestSwipeInstantiation:
    def test_can_instantiate_for_user_target(self):
        from app.models.swipe import Swipe, SwipeAction

        swipe = Swipe(swiper_id=1, target_user_id=2, action=SwipeAction.LIKE)

        assert swipe.swiper_id == 1
        assert swipe.target_user_id == 2
        assert swipe.target_pack_id is None
        assert swipe.action == SwipeAction.LIKE

    def test_can_instantiate_for_pack_target(self):
        from app.models.swipe import Swipe, SwipeAction

        swipe = Swipe(swiper_id=1, target_pack_id=4, action=SwipeAction.PASS)

        assert swipe.swiper_id == 1
        assert swipe.target_user_id is None
        assert swipe.target_pack_id == 4
        assert swipe.action == SwipeAction.PASS


class TestSwipeEnum:
    def test_swipe_action_values_match_schema(self):
        from app.models.swipe import SwipeAction

        assert SwipeAction.LIKE.value == "like"
        assert SwipeAction.PASS.value == "pass"


class TestSwipeInBase:
    def test_swipe_table_registered_in_metadata(self):
        from app.database import Base
        from app.models.swipe import Swipe  # noqa: F401 - ensures registration

        assert "swipes" in Base.metadata.tables
