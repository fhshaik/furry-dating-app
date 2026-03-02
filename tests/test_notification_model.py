"""Tests for the Notification SQLAlchemy model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


BACKEND_DIR = Path(__file__).parent.parent / "backend"
NOTIFICATIONS_MIGRATION = BACKEND_DIR / "alembic" / "versions" / "0006_add_notifications.py"


class TestNotificationImport:
    def test_notification_is_importable(self):
        from app.models.notification import Notification

        assert Notification is not None

    def test_notification_is_exported(self):
        from app.models import Notification

        assert Notification is not None


class TestNotificationTableName:
    def test_tablename_is_notifications(self):
        from app.models.notification import Notification

        assert Notification.__tablename__ == "notifications"


class TestNotificationColumns:
    def test_has_id_column(self):
        from app.models.notification import Notification

        assert hasattr(Notification, "id")

    def test_has_user_id_column(self):
        from app.models.notification import Notification

        assert hasattr(Notification, "user_id")

    def test_has_type_column(self):
        from app.models.notification import Notification

        assert hasattr(Notification, "type")

    def test_has_payload_column(self):
        from app.models.notification import Notification

        assert hasattr(Notification, "payload")

    def test_has_is_read_column(self):
        from app.models.notification import Notification

        assert hasattr(Notification, "is_read")

    def test_has_created_at_column(self):
        from app.models.notification import Notification

        assert hasattr(Notification, "created_at")


class TestNotificationColumnTypes:
    def _get_col(self, model, col_name):
        return model.__table__.c[col_name]

    def test_id_is_integer_primary_key(self):
        from sqlalchemy import Integer

        from app.models.notification import Notification

        col = self._get_col(Notification, "id")
        assert isinstance(col.type, Integer)
        assert col.primary_key

    def test_user_id_is_integer(self):
        from sqlalchemy import Integer

        from app.models.notification import Notification

        col = self._get_col(Notification, "user_id")
        assert isinstance(col.type, Integer)
        assert not col.nullable

    def test_type_is_string(self):
        from sqlalchemy import String

        from app.models.notification import Notification

        col = self._get_col(Notification, "type")
        assert isinstance(col.type, String)
        assert col.type.length == 50
        assert not col.nullable

    def test_payload_is_json(self):
        from sqlalchemy import JSON

        from app.models.notification import Notification

        col = self._get_col(Notification, "payload")
        assert isinstance(col.type, JSON)
        assert not col.nullable

    def test_is_read_is_boolean(self):
        from sqlalchemy import Boolean

        from app.models.notification import Notification

        col = self._get_col(Notification, "is_read")
        assert isinstance(col.type, Boolean)
        assert not col.nullable

    def test_created_at_is_datetime(self):
        from sqlalchemy import DateTime

        from app.models.notification import Notification

        col = self._get_col(Notification, "created_at")
        assert isinstance(col.type, DateTime)
        assert not col.nullable


class TestNotificationDefaults:
    def test_is_read_has_server_default_false(self):
        from app.models.notification import Notification

        col = Notification.__table__.c["is_read"]
        assert col.server_default is not None
        assert col.server_default.arg == "0"

    def test_created_at_has_server_default(self):
        from app.models.notification import Notification

        col = Notification.__table__.c["created_at"]
        assert col.server_default is not None


class TestNotificationForeignKeys:
    def test_user_id_has_foreign_key_to_users(self):
        from app.models.notification import Notification

        col = Notification.__table__.c["user_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "users.id" in fk_targets

    def test_user_id_foreign_key_cascades_on_delete(self):
        from app.models.notification import Notification

        user_fks = Notification.__table__.c["user_id"].foreign_keys
        assert next(iter(user_fks)).ondelete == "CASCADE"


class TestNotificationInstantiation:
    def test_can_instantiate_with_required_fields(self):
        from app.models.notification import Notification

        notification = Notification(
            user_id=1,
            type="match_created",
            payload={"match_id": 123},
        )

        assert notification.user_id == 1
        assert notification.type == "match_created"
        assert notification.payload == {"match_id": 123}


class TestNotificationInBase:
    def test_notification_table_registered_in_metadata(self):
        from app.database import Base
        from app.models.notification import Notification  # noqa: F401

        assert "notifications" in Base.metadata.tables


class TestNotificationMigration:
    def test_notifications_migration_exists(self):
        assert NOTIFICATIONS_MIGRATION.exists()

    def test_notifications_migration_has_expected_revision_chain(self):
        content = NOTIFICATIONS_MIGRATION.read_text()
        assert 'revision: str = "0006"' in content
        assert 'down_revision: Union[str, None] = "0005"' in content

    def test_notifications_migration_creates_expected_columns(self):
        content = NOTIFICATIONS_MIGRATION.read_text()
        assert '"notifications"' in content
        assert '"user_id"' in content
        assert '"type"' in content
        assert '"payload"' in content
        assert '"is_read"' in content
