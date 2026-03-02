"""Tests for Alembic migration setup and initial schema migration."""

import importlib
from pathlib import Path


BACKEND_DIR = Path(__file__).parent.parent / "backend"
ALEMBIC_DIR = BACKEND_DIR / "alembic"
VERSIONS_DIR = ALEMBIC_DIR / "versions"
INITIAL_MIGRATION = VERSIONS_DIR / "0001_initial_schema.py"
PACK_JOIN_REQUEST_VOTES_MIGRATION = VERSIONS_DIR / "0004_add_pack_join_request_votes.py"
REPORTS_MIGRATION = VERSIONS_DIR / "0007_add_reports.py"


class TestAlembicIni:
    def test_alembic_ini_exists(self):
        assert (BACKEND_DIR / "alembic.ini").exists()

    def test_alembic_ini_has_script_location(self):
        content = (BACKEND_DIR / "alembic.ini").read_text()
        assert "script_location = alembic" in content

    def test_alembic_ini_has_prepend_sys_path(self):
        content = (BACKEND_DIR / "alembic.ini").read_text()
        assert "prepend_sys_path = ." in content

    def test_alembic_ini_has_logger_sections(self):
        content = (BACKEND_DIR / "alembic.ini").read_text()
        assert "[logger_alembic]" in content
        assert "[logger_sqlalchemy]" in content


class TestAlembicDirectory:
    def test_alembic_dir_exists(self):
        assert ALEMBIC_DIR.is_dir()

    def test_env_py_exists(self):
        assert (ALEMBIC_DIR / "env.py").exists()

    def test_script_mako_exists(self):
        assert (ALEMBIC_DIR / "script.py.mako").exists()

    def test_versions_dir_exists(self):
        assert VERSIONS_DIR.is_dir()


class TestAlembicEnvPy:
    def test_env_py_imports_models(self):
        content = (ALEMBIC_DIR / "env.py").read_text()
        assert "import app.models" in content

    def test_env_py_imports_base(self):
        content = (ALEMBIC_DIR / "env.py").read_text()
        assert "from app.database import Base" in content

    def test_env_py_imports_settings(self):
        content = (ALEMBIC_DIR / "env.py").read_text()
        assert "from app.core.config import settings" in content

    def test_env_py_sets_target_metadata(self):
        content = (ALEMBIC_DIR / "env.py").read_text()
        assert "target_metadata = Base.metadata" in content

    def test_env_py_has_offline_mode(self):
        content = (ALEMBIC_DIR / "env.py").read_text()
        assert "run_migrations_offline" in content

    def test_env_py_has_online_mode(self):
        content = (ALEMBIC_DIR / "env.py").read_text()
        assert "run_migrations_online" in content

    def test_env_py_uses_async_engine(self):
        content = (ALEMBIC_DIR / "env.py").read_text()
        assert "create_async_engine" in content

    def test_env_py_uses_run_sync(self):
        content = (ALEMBIC_DIR / "env.py").read_text()
        assert "run_sync" in content


class TestInitialMigration:
    def test_migration_file_exists(self):
        assert INITIAL_MIGRATION.exists()

    def test_migration_has_correct_revision(self):
        content = INITIAL_MIGRATION.read_text()
        assert 'revision: str = "0001"' in content

    def test_migration_has_no_down_revision(self):
        content = INITIAL_MIGRATION.read_text()
        assert "down_revision: Union[str, None] = None" in content

    def test_migration_has_upgrade_function(self):
        content = INITIAL_MIGRATION.read_text()
        assert "def upgrade() -> None:" in content

    def test_migration_has_downgrade_function(self):
        content = INITIAL_MIGRATION.read_text()
        assert "def downgrade() -> None:" in content

    def test_migration_is_importable(self):
        import sys

        sys.path.insert(0, str(VERSIONS_DIR))
        spec = importlib.util.spec_from_file_location("migration_0001", INITIAL_MIGRATION)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, "upgrade")
        assert hasattr(module, "downgrade")
        assert callable(module.upgrade)
        assert callable(module.downgrade)

    def test_migration_creates_users_table(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"users"' in content

    def test_migration_creates_fursonas_table(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"fursonas"' in content

    def test_migration_creates_species_tags_table(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"species_tags"' in content

    def test_migration_creates_items_table(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"items"' in content

    def test_migration_creates_swipes_table(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"swipes"' in content

    def test_migration_creates_matches_table(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"matches"' in content

    def test_migration_creates_packs_table(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"packs"' in content

    def test_migration_creates_pack_members_table(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"pack_members"' in content

    def test_migration_creates_pack_join_requests_table(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"pack_join_requests"' in content

    def test_migration_creates_conversations_table(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"conversations"' in content

    def test_migration_creates_conversation_members_table(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"conversation_members"' in content

    def test_initial_migration_does_not_create_messages_table(self):
        content = INITIAL_MIGRATION.read_text()
        assert 'op.create_table(\n        "messages"' not in content

    def test_migration_creates_messages_table(self):
        content = (VERSIONS_DIR / "0005_add_messages.py").read_text()
        assert '"messages"' in content

    def test_downgrade_drops_tables_in_reverse_order(self):
        content = INITIAL_MIGRATION.read_text()
        downgrade_section = content[content.index("def downgrade()") :]
        conversation_members_pos = downgrade_section.index('"conversation_members"')
        users_pos = downgrade_section.index('"users"')
        assert conversation_members_pos < users_pos

    def test_migration_users_has_oauth_columns(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"oauth_provider"' in content
        assert '"oauth_id"' in content

    def test_migration_fursonas_has_is_primary(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"is_primary"' in content

    def test_migration_fursonas_has_is_nsfw(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"is_nsfw"' in content

    def test_migration_packs_has_consensus_required(self):
        content = INITIAL_MIGRATION.read_text()
        assert '"consensus_required"' in content

    def test_migration_messages_has_is_read(self):
        content = (VERSIONS_DIR / "0005_add_messages.py").read_text()
        assert '"is_read"' in content

    def test_migration_revision_chain_is_linear(self):
        expected_chain = {
            "0001_initial_schema.py": 'down_revision: Union[str, None] = None',
            "0002_add_relationship_style.py": 'down_revision: Union[str, None] = "0001"',
            "0003_seed_species_tags.py": 'down_revision: Union[str, None] = "0002"',
            "0004_add_pack_join_request_votes.py": 'down_revision: Union[str, None] = "0003"',
            "0005_add_messages.py": 'down_revision: Union[str, None] = "0004"',
            "0006_add_notifications.py": 'down_revision: Union[str, None] = "0005"',
            "0007_add_reports.py": 'down_revision: Union[str, None] = "0006"',
            "0008_seed_example_data.py": 'down_revision: Union[str, None] = "0007"',
        }
        for filename, down_revision in expected_chain.items():
            content = (VERSIONS_DIR / filename).read_text()
            assert down_revision in content


class TestPackJoinRequestVotesMigration:
    def test_migration_file_exists(self):
        assert PACK_JOIN_REQUEST_VOTES_MIGRATION.exists()

    def test_migration_creates_pack_join_request_votes_table(self):
        content = PACK_JOIN_REQUEST_VOTES_MIGRATION.read_text()
        assert '"pack_join_request_votes"' in content
        assert '"join_request_vote_decision"' in content


class TestReportsMigration:
    def test_migration_file_exists(self):
        assert REPORTS_MIGRATION.exists()

    def test_migration_creates_reports_table(self):
        content = REPORTS_MIGRATION.read_text()
        assert '"reports"' in content
        assert '"reporter_id"' in content
        assert '"reported_user_id"' in content
