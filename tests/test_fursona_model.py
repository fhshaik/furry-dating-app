"""Tests for the Fursona SQLAlchemy model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestFursonaImport:
    def test_fursona_is_importable(self):
        from app.models.fursona import Fursona

        assert Fursona is not None

    def test_fursona_importable_from_models_package(self):
        from app.models import Fursona

        assert Fursona is not None

    def test_fursona_in_models_all(self):
        import app.models as models

        assert "Fursona" in models.__all__


class TestFursonaTableName:
    def test_tablename_is_fursonas(self):
        from app.models.fursona import Fursona

        assert Fursona.__tablename__ == "fursonas"


class TestFursonaColumns:
    def test_has_id_column(self):
        from app.models.fursona import Fursona

        assert hasattr(Fursona, "id")

    def test_has_user_id_column(self):
        from app.models.fursona import Fursona

        assert hasattr(Fursona, "user_id")

    def test_has_name_column(self):
        from app.models.fursona import Fursona

        assert hasattr(Fursona, "name")

    def test_has_species_column(self):
        from app.models.fursona import Fursona

        assert hasattr(Fursona, "species")

    def test_has_traits_column(self):
        from app.models.fursona import Fursona

        assert hasattr(Fursona, "traits")

    def test_has_description_column(self):
        from app.models.fursona import Fursona

        assert hasattr(Fursona, "description")

    def test_has_image_url_column(self):
        from app.models.fursona import Fursona

        assert hasattr(Fursona, "image_url")

    def test_has_is_primary_column(self):
        from app.models.fursona import Fursona

        assert hasattr(Fursona, "is_primary")

    def test_has_is_nsfw_column(self):
        from app.models.fursona import Fursona

        assert hasattr(Fursona, "is_nsfw")

    def test_has_created_at_column(self):
        from app.models.fursona import Fursona

        assert hasattr(Fursona, "created_at")


class TestFursonaColumnTypes:
    def _get_col(self, model, col_name):
        return model.__table__.c[col_name]

    def test_id_is_integer_primary_key(self):
        from sqlalchemy import Integer
        from app.models.fursona import Fursona

        col = self._get_col(Fursona, "id")
        assert isinstance(col.type, Integer)
        assert col.primary_key

    def test_user_id_is_integer(self):
        from sqlalchemy import Integer
        from app.models.fursona import Fursona

        col = self._get_col(Fursona, "user_id")
        assert isinstance(col.type, Integer)
        assert not col.nullable

    def test_name_is_string_not_nullable(self):
        from sqlalchemy import String
        from app.models.fursona import Fursona

        col = self._get_col(Fursona, "name")
        assert isinstance(col.type, String)
        assert col.type.length == 100
        assert not col.nullable

    def test_species_is_string_not_nullable(self):
        from sqlalchemy import String
        from app.models.fursona import Fursona

        col = self._get_col(Fursona, "species")
        assert isinstance(col.type, String)
        assert col.type.length == 100
        assert not col.nullable

    def test_traits_is_json_nullable(self):
        from sqlalchemy import JSON
        from app.models.fursona import Fursona

        col = self._get_col(Fursona, "traits")
        assert isinstance(col.type, JSON)
        assert col.nullable

    def test_description_is_text_nullable(self):
        from sqlalchemy import Text
        from app.models.fursona import Fursona

        col = self._get_col(Fursona, "description")
        assert isinstance(col.type, Text)
        assert col.nullable

    def test_image_url_is_string_nullable(self):
        from sqlalchemy import String
        from app.models.fursona import Fursona

        col = self._get_col(Fursona, "image_url")
        assert isinstance(col.type, String)
        assert col.type.length == 500
        assert col.nullable

    def test_is_primary_is_boolean_not_nullable(self):
        from sqlalchemy import Boolean
        from app.models.fursona import Fursona

        col = self._get_col(Fursona, "is_primary")
        assert isinstance(col.type, Boolean)
        assert not col.nullable

    def test_is_nsfw_is_boolean_not_nullable(self):
        from sqlalchemy import Boolean
        from app.models.fursona import Fursona

        col = self._get_col(Fursona, "is_nsfw")
        assert isinstance(col.type, Boolean)
        assert not col.nullable

    def test_created_at_is_datetime_not_nullable(self):
        from sqlalchemy import DateTime
        from app.models.fursona import Fursona

        col = self._get_col(Fursona, "created_at")
        assert isinstance(col.type, DateTime)
        assert not col.nullable


class TestFursonaDefaults:
    def test_is_primary_has_server_default_false(self):
        from app.models.fursona import Fursona

        col = Fursona.__table__.c["is_primary"]
        assert col.server_default is not None
        assert col.server_default.arg == "0"

    def test_is_nsfw_has_server_default_false(self):
        from app.models.fursona import Fursona

        col = Fursona.__table__.c["is_nsfw"]
        assert col.server_default is not None
        assert col.server_default.arg == "0"

    def test_created_at_has_server_default(self):
        from app.models.fursona import Fursona

        col = Fursona.__table__.c["created_at"]
        assert col.server_default is not None


class TestFursonaForeignKey:
    def test_user_id_has_foreign_key_to_users(self):
        from app.models.fursona import Fursona

        col = Fursona.__table__.c["user_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "users.id" in fk_targets

    def test_user_id_foreign_key_cascades_on_delete(self):
        from app.models.fursona import Fursona

        col = Fursona.__table__.c["user_id"]
        for fk in col.foreign_keys:
            if fk.target_fullname == "users.id":
                assert fk.ondelete == "CASCADE"
                break


class TestFursonaInstantiation:
    def test_can_instantiate_with_required_fields(self):
        from app.models.fursona import Fursona

        fursona = Fursona(user_id=1, name="Ember", species="Fox")
        assert fursona.name == "Ember"
        assert fursona.species == "Fox"
        assert fursona.user_id == 1

    def test_can_set_optional_fields(self):
        from app.models.fursona import Fursona

        fursona = Fursona(
            user_id=1,
            name="Ember",
            species="Fox",
            traits=["friendly", "adventurous"],
            description="A fiery fox",
            image_url="https://example.com/ember.png",
            is_primary=True,
            is_nsfw=False,
        )
        assert fursona.traits == ["friendly", "adventurous"]
        assert fursona.description == "A fiery fox"
        assert fursona.image_url == "https://example.com/ember.png"
        assert fursona.is_primary is True
        assert fursona.is_nsfw is False

    def test_traits_accepts_dict(self):
        from app.models.fursona import Fursona

        traits = {"personality": "playful", "colors": ["orange", "white"]}
        fursona = Fursona(user_id=1, name="Ember", species="Fox", traits=traits)
        assert fursona.traits == traits

    def test_traits_accepts_none(self):
        from app.models.fursona import Fursona

        fursona = Fursona(user_id=1, name="Ember", species="Fox", traits=None)
        assert fursona.traits is None

    def test_description_accepts_none(self):
        from app.models.fursona import Fursona

        fursona = Fursona(user_id=1, name="Ember", species="Fox", description=None)
        assert fursona.description is None

    def test_image_url_accepts_none(self):
        from app.models.fursona import Fursona

        fursona = Fursona(user_id=1, name="Ember", species="Fox", image_url=None)
        assert fursona.image_url is None


class TestFursonaInBase:
    def test_fursona_table_registered_in_metadata(self):
        from app.database import Base
        from app.models.fursona import Fursona  # noqa: F401 — ensures registration

        assert "fursonas" in Base.metadata.tables
