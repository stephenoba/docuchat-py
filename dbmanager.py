import uuid
import logging
from datetime import datetime

from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import joinedload, selectinload

from config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
# Ensure using aiosqlite for SQLite
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("sqlite:///"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class DBManager:
    def __init__(self):
        self.engine = engine

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

    async def all(self):
        async with async_session() as session:
            statement = select(self.model)
            result = await session.execute(statement)
            return result.scalars().all()

    async def get(self, **kwargs):
        async with async_session() as session:
            statement = select(self.model).filter_by(**kwargs)
            result = await session.execute(statement)
            return result.scalars().first()

    async def get_by_id(self, id: bytes | str | uuid.UUID):
        async with async_session() as session:
            return await session.get(self.model, id)

    async def select_related(self, *args):
        async with async_session() as session:
            statement = select(self.model).options(selectinload(*args))
            result = await session.execute(statement)
            return result.scalars().all()

    async def select_joined(self, *args):
        async with async_session() as session:
            statement = select(self.model).options(joinedload(*args))
            result = await session.execute(statement)
            return result.scalars().all()

    async def create(self, **kwargs):
        model = self.model(**kwargs)
        return await self.save(model)

    async def update(self, model: SQLModel):
        if hasattr(model, "updated_at"):
            model.updated_at = datetime.now()
        return await self.save(model)

    async def delete(self, model: SQLModel):
        async with async_session() as session:
            await session.delete(model)
            await session.commit()
            return True

    async def delete_all(self):
        async with async_session() as session:
            try:
                # For simplicity in delete_all, we can use traditional query or execute delete
                from sqlalchemy import delete
                await session.execute(delete(self.model))
                await session.commit()
                return True
            except Exception as e:
                logger.error(f"Error deleting all {self.model.__name__}s: {e}")
                await session.rollback()
                return False

    async def save(self, model: SQLModel):
        async with async_session() as session:
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model


class UserManager(QueryManager):
    async def create(self, **kwargs):
        kwargs["username"] = kwargs["email"]
        return await super().create(**kwargs)