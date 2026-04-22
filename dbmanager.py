from datetime import datetime

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.orm import joinedload, selectinload

from config import get_settings

settings = get_settings()
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)


class DBManager:
    def __init__(self):
        self.engine = engine

    def create_db_and_tables(self):
        SQLModel.metadata.create_all(self.engine)

    def drop_db_and_tables(self):
        SQLModel.metadata.drop_all(self.engine)


class QueryManager(DBManager):
    def __init__(self, session: Session = None):
        super().__init__()
        self.session = session
        self.model = None

    def __set_name__(self, owner, name):
        self.model = owner

    def all(self):
        with Session(self.engine) as session:
            return session.query(self.model).all()

    def get(self, **kwargs):
        with Session(self.engine) as session:
            return session.query(self.model).filter_by(**kwargs).first()

    def get_by_id(self, id: int):
        with Session(self.engine) as session:
            return session.get(self.model, id)

    def select_related(self, *args):
        with Session(self.engine) as session:
            return session.query(self.model).options(selectinload(*args)).all()

    def select_joined(self, *args):
        with Session(self.engine) as session:
            return session.query(self.model).options(joinedload(*args)).all()

    def create(self, **kwargs):
        model = self.model(**kwargs)
        return self.save(model)

    def update(self, model: SQLModel):
        if hasattr(model, "updated_at"):
            model.updated_at = datetime.now()
        return self.save(model)

    def delete(self, model: SQLModel):
        with Session(self.engine) as session:
            session.delete(model)
            session.commit()
            return True

    def delete_all(self):
        with Session(self.engine) as session:
            try:
                session.query(self.model).delete()
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                return False

    def save(self, model: SQLModel):
        with Session(self.engine) as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            return model


class UserManager(QueryManager):
    def create(self, **kwargs):
        kwargs["username"] = kwargs["email"]
        return super().create(**kwargs)