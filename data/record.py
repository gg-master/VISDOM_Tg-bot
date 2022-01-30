import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class RecordModel(SqlAlchemyBase):
    __tablename__ = 'record'

    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True,
                           primary_key=True)
    time = sqlalchemy.Column(sqlalchemy.Time)
    sys_press = sqlalchemy.Column(sqlalchemy.Integer)
    dias_press = sqlalchemy.Column(sqlalchemy.Integer)
    heart_rate = sqlalchemy.Column(sqlalchemy.Integer)
    time_zone = sqlalchemy.Column(sqlalchemy.Integer)
    accept_time_id = sqlalchemy.Column(sqlalchemy.Integer,
                                    sqlalchemy.ForeignKey('accept_time.id'))
    accept_time = orm.relation('AcceptTimeModel')




