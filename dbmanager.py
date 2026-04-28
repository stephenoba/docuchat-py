import uuid
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from sqlmodel import SQLModel, select
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import joinedload, selectinload

from config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
# Ensure using aiosqlite for SQLite
DATABASE_URL = settings.DATABASE_URL
# DB URL for celery since celery doesn't work with async
CELERY_DATABASE_URL = DATABASE_URL

if DATABASE_URL.startswith("sqlite:///"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

sync_engine = create_engine(CELERY_DATABASE_URL, echo=settings.DEBUG)
async_engine = create_async_engine(DATABASE_URL, echo=settings.DEBUG)

async_session = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


class DBManager:
    def __init__(self):
        self.engine = async_engine

    async def create_db_and_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def drop_db_and_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)


class QueryManager(DBManager):
    def __init__(self):
        super().__init__()
        self.model = None

    def __set_name__(self, owner, name):
        self.model = owner

    @asynccontextmanager
    async def _session(self, session: AsyncSession = None):
        if session:
            yield session
        else:
            async with async_session() as s:
                yield s

    async def all(self, session: AsyncSession = None):
        async with self._session(session) as s:
            statement = select(self.model)
            result = await s.execute(statement)
            return result.scalars().all()

    async def get(self, session: AsyncSession = None, **kwargs):
        async with self._session(session) as s:
            statement = select(self.model).filter_by(**kwargs)
            result = await s.execute(statement)
            return result.scalars().first()

    async def get_by_id(
        self, id: bytes | str | uuid.UUID, session: AsyncSession = None
    ):
        async with self._session(session) as s:
            return await s.get(self.model, id)

    async def select_related(self, *args, session: AsyncSession = None):
        async with self._session(session) as s:
            statement = select(self.model).options(selectinload(*args))
            result = await s.execute(statement)
            return result.scalars().all()

    async def select_joined(self, *args, session: AsyncSession = None):
        async with self._session(session) as s:
            statement = select(self.model).options(joinedload(*args))
            result = await s.execute(statement)
            return result.scalars().all()

    async def create(self, session: AsyncSession = None, **kwargs):
        model = self.model(**kwargs)
        return await self.save(model, session=session)

    async def update(self, model: SQLModel, session: AsyncSession = None):
        if hasattr(model, "updated_at"):
            model.updated_at = datetime.now()
        return await self.save(model, session=session)

    async def delete(self, model: SQLModel, session: AsyncSession = None):
        async with self._session(session) as s:
            await s.delete(model)
            if not session:
                await s.commit()
            return True

    async def delete_all(self, session: AsyncSession = None):
        async with self._session(session) as s:
            try:
                from sqlalchemy import delete

                await s.execute(delete(self.model))
                if not session:
                    await s.commit()
                return True
            except Exception as e:
                logger.error(f"Error deleting all {self.model.__name__}s: {e}")
                if not session:
                    await s.rollback()
                return False

    async def save(self, model: SQLModel, session: AsyncSession = None):
        async with self._session(session) as s:
            s.add(model)
            if not session:
                await s.commit()
                await s.refresh(model)
            return model


class UserManager(QueryManager):
    async def create(self, session: AsyncSession = None, **kwargs):
        kwargs["username"] = kwargs["email"]
        return await super().create(session=session, **kwargs)
