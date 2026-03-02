"""Tests for the /api/items CRUD router."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2024, 1, 15, 12, 0, 0)


def _make_item(id: int = 1, name: str = "Widget", description: str | None = "A widget") -> MagicMock:
    item = MagicMock()
    item.id = id
    item.name = name
    item.description = description
    item.created_at = _NOW
    return item


def _make_db_mock() -> AsyncMock:
    mock = AsyncMock()
    mock.get = AsyncMock()
    mock.add = MagicMock()
    mock.commit = AsyncMock()
    mock.refresh = AsyncMock()
    mock.delete = AsyncMock()
    mock.execute = AsyncMock()
    return mock


def _make_client_with_db(db_mock: AsyncMock) -> TestClient:
    from app.database import get_db
    from app.main import app

    async def override_get_db():
        yield db_mock

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app, raise_server_exceptions=True)
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# List items  GET /api/items
# ---------------------------------------------------------------------------


class TestListItems:
    def test_list_returns_200(self):
        db = _make_db_mock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        for client in _make_client_with_db(db):
            response = client.get("/api/items")
        assert response.status_code == 200

    def test_list_returns_empty_list_when_no_items(self):
        db = _make_db_mock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        for client in _make_client_with_db(db):
            response = client.get("/api/items")
        assert response.json() == []

    def test_list_returns_items(self):
        db = _make_db_mock()
        item = _make_item()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [item]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        for client in _make_client_with_db(db):
            response = client.get("/api/items")
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Widget"
        assert data[0]["description"] == "A widget"

    def test_list_content_type_is_json(self):
        db = _make_db_mock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        for client in _make_client_with_db(db):
            response = client.get("/api/items")
        assert "application/json" in response.headers["content-type"]

    def test_list_passes_skip_and_limit(self):
        db = _make_db_mock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        for client in _make_client_with_db(db):
            response = client.get("/api/items?skip=5&limit=10")
        assert response.status_code == 200
        db.execute.assert_called_once()


# ---------------------------------------------------------------------------
# Create item  POST /api/items
# ---------------------------------------------------------------------------


class TestCreateItem:
    def test_create_returns_201(self):
        db = _make_db_mock()
        created = _make_item()

        async def side_effect_refresh(obj):
            obj.id = created.id
            obj.name = created.name
            obj.description = created.description
            obj.created_at = created.created_at

        db.refresh = AsyncMock(side_effect=side_effect_refresh)

        for client in _make_client_with_db(db):
            response = client.post("/api/items", json={"name": "Widget", "description": "A widget"})
        assert response.status_code == 201

    def test_create_returns_item_data(self):
        db = _make_db_mock()

        async def side_effect_refresh(obj):
            obj.id = 1
            obj.created_at = _NOW

        db.refresh = AsyncMock(side_effect=side_effect_refresh)

        for client in _make_client_with_db(db):
            response = client.post("/api/items", json={"name": "Widget", "description": "A widget"})
        data = response.json()
        assert data["name"] == "Widget"
        assert data["description"] == "A widget"
        assert "id" in data
        assert "created_at" in data

    def test_create_with_no_description(self):
        db = _make_db_mock()

        async def side_effect_refresh(obj):
            obj.id = 2
            obj.created_at = _NOW

        db.refresh = AsyncMock(side_effect=side_effect_refresh)

        for client in _make_client_with_db(db):
            response = client.post("/api/items", json={"name": "Minimal"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal"

    def test_create_commits_to_db(self):
        db = _make_db_mock()

        async def side_effect_refresh(obj):
            obj.id = 1
            obj.created_at = _NOW

        db.refresh = AsyncMock(side_effect=side_effect_refresh)

        for client in _make_client_with_db(db):
            client.post("/api/items", json={"name": "Widget"})
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_create_rejects_empty_name(self):
        db = _make_db_mock()

        for client in _make_client_with_db(db):
            response = client.post("/api/items", json={"name": ""})
        assert response.status_code == 422

    def test_create_rejects_missing_name(self):
        db = _make_db_mock()

        for client in _make_client_with_db(db):
            response = client.post("/api/items", json={"description": "No name"})
        assert response.status_code == 422

    def test_create_trims_name_and_normalizes_blank_description(self):
        db = _make_db_mock()

        async def side_effect_refresh(obj):
            obj.id = 3
            obj.created_at = _NOW

        db.refresh = AsyncMock(side_effect=side_effect_refresh)

        for client in _make_client_with_db(db):
            response = client.post(
                "/api/items",
                json={"name": "  Widget  ", "description": "   "},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Widget"
        assert data["description"] is None


# ---------------------------------------------------------------------------
# Get item  GET /api/items/{item_id}
# ---------------------------------------------------------------------------


class TestGetItem:
    def test_get_existing_item_returns_200(self):
        db = _make_db_mock()
        db.get = AsyncMock(return_value=_make_item())

        for client in _make_client_with_db(db):
            response = client.get("/api/items/1")
        assert response.status_code == 200

    def test_get_existing_item_returns_data(self):
        db = _make_db_mock()
        db.get = AsyncMock(return_value=_make_item(id=1, name="Widget"))

        for client in _make_client_with_db(db):
            response = client.get("/api/items/1")
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Widget"

    def test_get_missing_item_returns_404(self):
        db = _make_db_mock()
        db.get = AsyncMock(return_value=None)

        for client in _make_client_with_db(db):
            response = client.get("/api/items/999")
        assert response.status_code == 404

    def test_get_missing_item_returns_detail(self):
        db = _make_db_mock()
        db.get = AsyncMock(return_value=None)

        for client in _make_client_with_db(db):
            response = client.get("/api/items/999")
        assert response.json()["detail"] == "Item not found"


# ---------------------------------------------------------------------------
# Update item  PUT /api/items/{item_id}
# ---------------------------------------------------------------------------


class TestUpdateItem:
    def test_update_existing_item_returns_200(self):
        db = _make_db_mock()
        item = _make_item()
        db.get = AsyncMock(return_value=item)

        async def side_effect_refresh(obj):
            pass

        db.refresh = AsyncMock(side_effect=side_effect_refresh)

        for client in _make_client_with_db(db):
            response = client.put("/api/items/1", json={"name": "Updated"})
        assert response.status_code == 200

    def test_update_modifies_name(self):
        db = _make_db_mock()
        item = _make_item(name="Old Name")
        db.get = AsyncMock(return_value=item)

        async def side_effect_refresh(obj):
            pass

        db.refresh = AsyncMock(side_effect=side_effect_refresh)

        for client in _make_client_with_db(db):
            client.put("/api/items/1", json={"name": "New Name"})
        assert item.name == "New Name"

    def test_update_modifies_description(self):
        db = _make_db_mock()
        item = _make_item(description="Old desc")
        db.get = AsyncMock(return_value=item)

        async def side_effect_refresh(obj):
            pass

        db.refresh = AsyncMock(side_effect=side_effect_refresh)

        for client in _make_client_with_db(db):
            client.put("/api/items/1", json={"description": "New desc"})
        assert item.description == "New desc"

    def test_update_missing_item_returns_404(self):
        db = _make_db_mock()
        db.get = AsyncMock(return_value=None)

        for client in _make_client_with_db(db):
            response = client.put("/api/items/999", json={"name": "X"})
        assert response.status_code == 404

    def test_update_rejects_null_name_with_422(self):
        """Sending name=null returns 422 since Item.name is non-nullable."""
        db = _make_db_mock()
        item = _make_item()
        db.get = AsyncMock(return_value=item)

        for client in _make_client_with_db(db):
            response = client.put("/api/items/1", json={"name": None})
        assert response.status_code == 422
        assert "name" in response.json()["detail"].lower()

    def test_update_commits_to_db(self):
        db = _make_db_mock()
        item = _make_item()
        db.get = AsyncMock(return_value=item)

        async def side_effect_refresh(obj):
            pass

        db.refresh = AsyncMock(side_effect=side_effect_refresh)

        for client in _make_client_with_db(db):
            client.put("/api/items/1", json={"name": "Updated"})
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_update_trims_name_and_clears_blank_description(self):
        db = _make_db_mock()
        item = _make_item(name="Old Name", description="Old desc")
        db.get = AsyncMock(return_value=item)

        async def side_effect_refresh(obj):
            pass

        db.refresh = AsyncMock(side_effect=side_effect_refresh)

        for client in _make_client_with_db(db):
            response = client.put(
                "/api/items/1",
                json={"name": "  New Name  ", "description": "   "},
            )

        assert response.status_code == 200
        assert item.name == "New Name"
        assert item.description is None


# ---------------------------------------------------------------------------
# Delete item  DELETE /api/items/{item_id}
# ---------------------------------------------------------------------------


class TestDeleteItem:
    def test_delete_existing_item_returns_204(self):
        db = _make_db_mock()
        db.get = AsyncMock(return_value=_make_item())

        for client in _make_client_with_db(db):
            response = client.delete("/api/items/1")
        assert response.status_code == 204

    def test_delete_existing_item_no_body(self):
        db = _make_db_mock()
        db.get = AsyncMock(return_value=_make_item())

        for client in _make_client_with_db(db):
            response = client.delete("/api/items/1")
        assert response.content == b""

    def test_delete_missing_item_returns_404(self):
        db = _make_db_mock()
        db.get = AsyncMock(return_value=None)

        for client in _make_client_with_db(db):
            response = client.delete("/api/items/999")
        assert response.status_code == 404

    def test_delete_calls_db_delete_and_commit(self):
        db = _make_db_mock()
        item = _make_item()
        db.get = AsyncMock(return_value=item)

        for client in _make_client_with_db(db):
            client.delete("/api/items/1")
        db.delete.assert_called_once_with(item)
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------


class TestItemsRouterRegistration:
    def test_items_router_in_app_routes(self):
        from app.main import app

        paths = [route.path for route in app.routes]
        assert "/api/items" in paths

    def test_items_detail_route_in_app_routes(self):
        from app.main import app

        paths = [route.path for route in app.routes]
        assert "/api/items/{item_id}" in paths
