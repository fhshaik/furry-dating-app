"""Tests for the Pack SQLAlchemy model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestPackImport:
    def test_pack_is_importable(self):
        from app.models.pack import Pack

        assert Pack is not None


class TestPackTableName:
    def test_tablename_is_packs(self):
        from app.models.pack import Pack

        assert Pack.__tablename__ == "packs"


class TestPackColumns:
    def test_has_id_column(self):
        from app.models.pack import Pack

        assert hasattr(Pack, "id")

    def test_has_creator_id_column(self):
        from app.models.pack import Pack

        assert hasattr(Pack, "creator_id")

    def test_has_name_column(self):
        from app.models.pack import Pack

        assert hasattr(Pack, "name")

    def test_has_description_column(self):
        from app.models.pack import Pack

        assert hasattr(Pack, "description")

    def test_has_image_url_column(self):
        from app.models.pack import Pack

        assert hasattr(Pack, "image_url")

    def test_has_species_tags_column(self):
        from app.models.pack import Pack

        assert hasattr(Pack, "species_tags")

    def test_has_max_size_column(self):
        from app.models.pack import Pack

        assert hasattr(Pack, "max_size")

    def test_has_consensus_required_column(self):
        from app.models.pack import Pack

        assert hasattr(Pack, "consensus_required")

    def test_has_is_open_column(self):
        from app.models.pack import Pack

        assert hasattr(Pack, "is_open")

    def test_has_created_at_column(self):
        from app.models.pack import Pack

        assert hasattr(Pack, "created_at")


class TestPackColumnTypes:
    def _get_col(self, model, col_name):
        return model.__table__.c[col_name]

    def test_id_is_integer_primary_key(self):
        from sqlalchemy import Integer

        from app.models.pack import Pack

        col = self._get_col(Pack, "id")
        assert isinstance(col.type, Integer)
        assert col.primary_key

    def test_creator_id_is_integer_not_nullable(self):
        from sqlalchemy import Integer

        from app.models.pack import Pack

        col = self._get_col(Pack, "creator_id")
        assert isinstance(col.type, Integer)
        assert not col.nullable

    def test_name_is_string_not_nullable(self):
        from sqlalchemy import String

        from app.models.pack import Pack

        col = self._get_col(Pack, "name")
        assert isinstance(col.type, String)
        assert col.type.length == 100
        assert not col.nullable

    def test_description_is_text_nullable(self):
        from sqlalchemy import Text

        from app.models.pack import Pack

        col = self._get_col(Pack, "description")
        assert isinstance(col.type, Text)
        assert col.nullable

    def test_image_url_is_string_nullable(self):
        from sqlalchemy import String

        from app.models.pack import Pack

        col = self._get_col(Pack, "image_url")
        assert isinstance(col.type, String)
        assert col.type.length == 500
        assert col.nullable

    def test_species_tags_is_json_nullable(self):
        from sqlalchemy import JSON

        from app.models.pack import Pack

        col = self._get_col(Pack, "species_tags")
        assert isinstance(col.type, JSON)
        assert col.nullable

    def test_max_size_is_integer_not_nullable(self):
        from sqlalchemy import Integer

        from app.models.pack import Pack

        col = self._get_col(Pack, "max_size")
        assert isinstance(col.type, Integer)
        assert not col.nullable

    def test_consensus_required_is_boolean_not_nullable(self):
        from sqlalchemy import Boolean

        from app.models.pack import Pack

        col = self._get_col(Pack, "consensus_required")
        assert isinstance(col.type, Boolean)
        assert not col.nullable

    def test_is_open_is_boolean_not_nullable(self):
        from sqlalchemy import Boolean

        from app.models.pack import Pack

        col = self._get_col(Pack, "is_open")
        assert isinstance(col.type, Boolean)
        assert not col.nullable

    def test_created_at_is_datetime_not_nullable(self):
        from sqlalchemy import DateTime

        from app.models.pack import Pack

        col = self._get_col(Pack, "created_at")
        assert isinstance(col.type, DateTime)
        assert not col.nullable


class TestPackDefaults:
    def test_max_size_has_server_default(self):
        from app.models.pack import Pack

        col = Pack.__table__.c["max_size"]
        assert col.server_default is not None
        assert col.server_default.arg == "10"

    def test_consensus_required_has_server_default_false(self):
        from app.models.pack import Pack

        col = Pack.__table__.c["consensus_required"]
        assert col.server_default is not None
        assert col.server_default.arg == "0"

    def test_is_open_has_server_default_true(self):
        from app.models.pack import Pack

        col = Pack.__table__.c["is_open"]
        assert col.server_default is not None
        assert col.server_default.arg == "1"

    def test_created_at_has_server_default(self):
        from app.models.pack import Pack

        col = Pack.__table__.c["created_at"]
        assert col.server_default is not None


class TestPackForeignKeys:
    def test_creator_id_has_foreign_key_to_users(self):
        from app.models.pack import Pack

        col = Pack.__table__.c["creator_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "users.id" in fk_targets

    def test_creator_id_foreign_key_restricts_on_delete(self):
        from app.models.pack import Pack

        creator_fks = Pack.__table__.c["creator_id"].foreign_keys
        assert next(iter(creator_fks)).ondelete == "RESTRICT"


class TestPackInstantiation:
    def test_can_instantiate_with_required_fields(self):
        from app.models.pack import Pack

        pack = Pack(creator_id=1, name="North Pack")

        assert pack.creator_id == 1
        assert pack.name == "North Pack"
        assert pack.description is None
        assert pack.image_url is None
        assert pack.species_tags is None

    def test_can_set_optional_fields(self):
        from app.models.pack import Pack

        pack = Pack(
            creator_id=1,
            name="Aurora Pack",
            description="A social pack",
            image_url="https://example.com/aurora-pack.png",
            species_tags=["wolf", "fox"],
            max_size=7,
            consensus_required=True,
            is_open=False,
        )

        assert pack.description == "A social pack"
        assert pack.image_url == "https://example.com/aurora-pack.png"
        assert pack.species_tags == ["wolf", "fox"]
        assert pack.max_size == 7
        assert pack.consensus_required is True
        assert pack.is_open is False


class TestPackInBase:
    def test_pack_table_registered_in_metadata(self):
        from app.database import Base
        from app.models.pack import Pack  # noqa: F401 - ensures registration

        assert "packs" in Base.metadata.tables
