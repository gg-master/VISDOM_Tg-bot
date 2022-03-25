import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Region(SqlAlchemyBase):
    __tablename__ = 'region'
    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True,
                           primary_key=True)
    chat_id = sqlalchemy.Column(sqlalchemy.BIGINT)
    region_code = sqlalchemy.Column(sqlalchemy.String(3))
    doctor = orm.relation('Doctor', back_populates='region',
                          passive_deletes='all')
