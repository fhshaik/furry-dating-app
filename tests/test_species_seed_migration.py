"""Tests for the species seed migration."""

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import sqlalchemy as sa


BACKEND_DIR = Path(__file__).parent.parent / "backend"
VERSIONS_DIR = BACKEND_DIR / "alembic" / "versions"
SEED_SPECIES_MIGRATION = VERSIONS_DIR / "0003_seed_species_tags.py"


def _load_migration_module(module_name: str, path: Path):
    sys.path.insert(0, str(VERSIONS_DIR))
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestSeedSpeciesTagsMigration:
    def test_migration_file_exists(self):
        assert SEED_SPECIES_MIGRATION.exists()

    def test_migration_seeds_sample_species_tags(self):
        module = _load_migration_module("migration_0003_samples", SEED_SPECIES_MIGRATION)

        assert len(module.SPECIES) >= 40
        assert ("Wolf", "wolf") in module.SPECIES
        assert ("Fox", "fox") in module.SPECIES
        assert ("Dragon", "dragon") in module.SPECIES
        assert ("Snow Leopard", "snow-leopard") in module.SPECIES

    def test_migration_species_names_and_slugs_are_unique(self):
        module = _load_migration_module("migration_0003_unique", SEED_SPECIES_MIGRATION)

        names = [name for name, _ in module.SPECIES]
        slugs = [slug for _, slug in module.SPECIES]

        assert len(names) == len(set(names))
        assert len(slugs) == len(set(slugs))

    def test_upgrade_inserts_only_missing_species_tags(self):
        module = _load_migration_module("migration_0003_upgrade", SEED_SPECIES_MIGRATION)
        bind = MagicMock()
        existing_slugs = {"wolf", "fox"}
        inserted_slugs: list[str] = []

        def execute_side_effect(statement):
            compiled = statement.compile()
            if statement.is_select:
                slug = next(value for key, value in compiled.params.items() if "slug" in key)
                result = MagicMock()
                result.scalar.return_value = 1 if slug in existing_slugs else None
                return result

            inserted_slugs.append(compiled.params["slug"])
            return MagicMock()

        bind.execute.side_effect = execute_side_effect
        module.op.get_bind = MagicMock(return_value=bind)

        module.upgrade()

        assert "wolf" not in inserted_slugs
        assert "fox" not in inserted_slugs
        expected_insert_count = len(module.SPECIES) - len(existing_slugs)
        assert len(inserted_slugs) == expected_insert_count

    def test_downgrade_deletes_seeded_species_tags(self):
        module = _load_migration_module("migration_0003_downgrade", SEED_SPECIES_MIGRATION)
        bind = MagicMock()
        deleted_slugs: list[str] = []

        def execute_side_effect(statement):
            compiled = statement.compile()
            if isinstance(statement, sa.sql.dml.Delete):
                deleted_slugs.append(next(iter(compiled.params.values())))
            return MagicMock()

        bind.execute.side_effect = execute_side_effect
        module.op.get_bind = MagicMock(return_value=bind)

        module.downgrade()

        assert deleted_slugs == [slug for _, slug in module.SPECIES]
