import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Region(SqlAlchemyBase):
    __tablename__ = 'region'
    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True,
                           primary_key=True)
    chat_id = sqlalchemy.Column(sqlalchemy.Integer)
    region_code = sqlalchemy.Column(sqlalchemy.Integer)
    doctor = orm.relation('Doctor', back_populates='region',
                          passive_deletes='all')
