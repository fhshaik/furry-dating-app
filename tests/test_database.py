"""Tests for the SQLAlchemy async database setup."""

import inspect

import pytest


class TestEngine:
    def test_engine_is_importable(self):
        from app.database import engine

        assert engine is not None

    def test_engine_url_uses_aiomysql_dialect(self):
        from app.database import engine

        url = str(engine.url)
        assert url.startswith("mysql+aiomysql://")

    def test_engine_url_contains_configured_host(self, monkeypatch):
        monkeypatch.setenv("MYSQL_HOST", "db.test.local")
        from app.core.config import Settings

        s = Settings()
        assert "db.test.local" in s.database_url

    def test_engine_url_contains_configured_database(self, monkeypatch):
        monkeypatch.setenv("MYSQL_DATABASE", "testdb")
        from app.core.config import Settings

        s = Settings()
        assert "testdb" in s.database_url

    def test_engine_url_contains_configured_port(self, monkeypatch):
        monkeypatch.setenv("MYSQL_PORT", "3307")
        from app.core.config import Settings

        s = Settings()
        assert "3307" in s.database_url

    def test_engine_pool_pre_ping_enabled(self):
        from app.database import engine

        assert engine.pool._pre_ping is True

    def test_engine_pool_size(self):
        from app.database import engine

        assert engine.pool.size() == 10

    def test_engine_max_overflow(self):
        from app.database import engine

        assert engine.pool._max_overflow == 20


class TestAsyncSessionLocal:
    def test_session_factory_is_importable(self):
        from app.database import AsyncSessionLocal

        assert AsyncSessionLocal is not None

    def test_session_factory_produces_async_session(self):
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from app.database import AsyncSessionLocal

        assert isinstance(AsyncSessionLocal, async_sessionmaker)

    def test_session_factory_expire_on_commit_false(self):
        from app.database import AsyncSessionLocal

        assert AsyncSessionLocal.kw.get("expire_on_commit") is False

    def test_session_factory_autocommit_false(self):
        from app.database import AsyncSessionLocal

        assert AsyncSessionLocal.kw.get("autocommit") is False

    def test_session_factory_autoflush_false(self):
        from app.database import AsyncSessionLocal

        assert AsyncSessionLocal.kw.get("autoflush") is False

    def test_session_factory_bound_to_engine(self):
        from app.database import AsyncSessionLocal, engine

        assert AsyncSessionLocal.kw.get("bind") is engine


class TestBase:
    def test_base_is_importable(self):
        from app.database import Base

        assert Base is not None

    def test_base_is_declarative_base(self):
        from sqlalchemy.orm import DeclarativeBase

        from app.database import Base

        assert issubclass(Base, DeclarativeBase)

    def test_base_has_metadata(self):
        from sqlalchemy import MetaData

        from app.database import Base

        assert isinstance(Base.metadata, MetaData)

    def test_subclass_of_base_has_tablename(self):
        from sqlalchemy import Column, Integer

        from app.database import Base

        class SampleModel(Base):
            __tablename__ = "sample"
            id = Column(Integer, primary_key=True)

        assert SampleModel.__tablename__ == "sample"


class TestGetDb:
    def test_get_db_is_importable(self):
        from app.database import get_db

        assert get_db is not None

    def test_get_db_is_async_generator_function(self):
        from app.database import get_db

        assert inspect.isasyncgenfunction(get_db)

    @pytest.mark.asyncio
    async def test_get_db_yields_async_session(self, monkeypatch):
        """get_db must yield an AsyncSession without hitting a real DB.

        We patch AsyncSessionLocal to return a mock context manager so no
        real MySQL connection is attempted.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from sqlalchemy.ext.asyncio import AsyncSession

        mock_session = MagicMock(spec=AsyncSession)
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.database.AsyncSessionLocal", return_value=mock_cm):
            from app.database import get_db

            gen = get_db()
            session = await gen.__anext__()
            assert session is mock_session
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass
