import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Patient(SqlAlchemyBase):
    __tablename__ = 'patient'

    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True,
                           primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String(45))
    user_code = sqlalchemy.Column(sqlalchemy.String(45),
                                  unique=True)
    time_zone = sqlalchemy.Column(sqlalchemy.Integer)
    chat_id = sqlalchemy.Column(sqlalchemy.String(45))
    member = sqlalchemy.Column(sqlalchemy.Boolean)
    # accept_time = orm.relationship('AcceptTime')
    patronage = orm.relationship("Patronage", secondary="patients_has_patronage",
                             backref="patient")


