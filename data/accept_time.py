import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class AcceptTime(SqlAlchemyBase):
    __tablename__ = 'accept_time'

    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True,
                           primary_key=True)
    patient_id = sqlalchemy.Column(sqlalchemy.Integer,
                                   sqlalchemy.ForeignKey('patient.id'))
    time = sqlalchemy.Column(sqlalchemy.Time)
    record = orm.relation('Record', back_populates='accept_time')
    patient = orm.relation('Patient')

