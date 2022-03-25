import sqlalchemy
from .db_session import SqlAlchemyBase


class University(SqlAlchemyBase):
    __tablename__ = 'university'
    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True,
                           primary_key=True)
    chat_id = sqlalchemy.Column(sqlalchemy.BIGINT)





