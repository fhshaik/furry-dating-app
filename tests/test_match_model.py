"""Tests for the Match SQLAlchemy model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestMatchImport:
    def test_match_is_importable(self):
        from app.models.match import Match

        assert Match is not None


class TestMatchTableName:
    def test_tablename_is_matches(self):
        from app.models.match import Match

        assert Match.__tablename__ == "matches"


class TestMatchColumns:
    def test_has_id_column(self):
        from app.models.match import Match

        assert hasattr(Match, "id")

    def test_has_user_a_id_column(self):
        from app.models.match import Match

        assert hasattr(Match, "user_a_id")

    def test_has_user_b_id_column(self):
        from app.models.match import Match

        assert hasattr(Match, "user_b_id")

    def test_has_created_at_column(self):
        from app.models.match import Match

        assert hasattr(Match, "created_at")

    def test_has_unmatched_at_column(self):
        from app.models.match import Match

        assert hasattr(Match, "unmatched_at")


class TestMatchColumnTypes:
    def _get_col(self, model, col_name):
        return model.__table__.c[col_name]

    def test_id_is_integer_primary_key(self):
        from sqlalchemy import Integer

        from app.models.match import Match

        col = self._get_col(Match, "id")
        assert isinstance(col.type, Integer)
        assert col.primary_key

    def test_user_a_id_is_integer_not_nullable(self):
        from sqlalchemy import Integer

        from app.models.match import Match

        col = self._get_col(Match, "user_a_id")
        assert isinstance(col.type, Integer)
        assert not col.nullable

    def test_user_b_id_is_integer_not_nullable(self):
        from sqlalchemy import Integer

        from app.models.match import Match

        col = self._get_col(Match, "user_b_id")
        assert isinstance(col.type, Integer)
        assert not col.nullable

    def test_created_at_is_datetime_not_nullable(self):
        from sqlalchemy import DateTime

        from app.models.match import Match

        col = self._get_col(Match, "created_at")
        assert isinstance(col.type, DateTime)
        assert not col.nullable

    def test_unmatched_at_is_datetime_nullable(self):
        from sqlalchemy import DateTime

        from app.models.match import Match

        col = self._get_col(Match, "unmatched_at")
        assert isinstance(col.type, DateTime)
        assert col.nullable


class TestMatchDefaults:
    def test_created_at_has_server_default(self):
        from app.models.match import Match

        col = Match.__table__.c["created_at"]
        assert col.server_default is not None


class TestMatchForeignKeys:
    def test_user_a_id_has_foreign_key_to_users(self):
        from app.models.match import Match

        col = Match.__table__.c["user_a_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "users.id" in fk_targets

    def test_user_b_id_has_foreign_key_to_users(self):
        from app.models.match import Match

        col = Match.__table__.c["user_b_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "users.id" in fk_targets

    def test_user_foreign_keys_cascade_on_delete(self):
        from app.models.match import Match

        user_a_fks = Match.__table__.c["user_a_id"].foreign_keys
        user_b_fks = Match.__table__.c["user_b_id"].foreign_keys

        assert next(iter(user_a_fks)).ondelete == "CASCADE"
        assert next(iter(user_b_fks)).ondelete == "CASCADE"


class TestMatchInstantiation:
    def test_can_instantiate_with_required_fields(self):
        from app.models.match import Match

        match = Match(user_a_id=1, user_b_id=2)

        assert match.user_a_id == 1
        assert match.user_b_id == 2
        assert match.unmatched_at is None


class TestMatchInBase:
    def test_match_table_registered_in_metadata(self):
        from app.database import Base
        from app.models.match import Match  # noqa: F401 - ensures registration

        assert "matches" in Base.metadata.tables
