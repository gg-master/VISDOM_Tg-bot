import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class PatientModel(SqlAlchemyBase):
    __tablename__ = 'patient'

    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True,
                           primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String(45))
    user_code = sqlalchemy.Column(sqlalchemy.String(45),
                                  unique=True)
    time_zone = sqlalchemy.Column(sqlalchemy.Integer)
    chat_id = sqlalchemy.Column(sqlalchemy.String(45), unique=True)
    member = sqlalchemy.Column(sqlalchemy.Boolean, default=True)
    accept_time = orm.relation('AcceptTimeModel', back_populates='patient')
    patronage = orm.relationship("PatronageModel",
                                 secondary="patients_has_patronage",
                                 back_populates="patient")


