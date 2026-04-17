from datetime import datetime

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.orm import joinedload, selectinload
from decouple import config as _config

import bcrypt

DATABASE_URL = _config("DATABASE_URL", default="sqlite:///../test.db", cast=str)
engine = create_engine(DATABASE_URL)

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

    def get_all(self):
        with Session(self.engine) as session:
            return session.query(self.model).all()

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
            session.query(self.model).delete()
            session.commit()
            return True

    def save(self, model: SQLModel):
        with Session(self.engine) as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            return model


class UserManager(QueryManager):
    def hash_password(self, password: str):
        password = password.encode("utf-8")
        
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password, salt)
        return hashed_password.decode("utf-8")
        

    def verify_password(self, password: str, hashed_password: str):
        password = password.encode("utf-8")
        hashed_password = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password, hashed_password)

    def create(self, **kwargs):
        kwargs["password_hash"] = self.hash_password(kwargs["password_hash"])
        return super().create(**kwargs)
        

    