import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase

association_table = sqlalchemy.Table(
    'patients_has_patronage', SqlAlchemyBase.metadata,
    sqlalchemy.Column('patient_id', sqlalchemy.Integer,
                      sqlalchemy.ForeignKey('patient.id')),
    sqlalchemy.Column('patronage_id', sqlalchemy.Integer,
                      sqlalchemy.ForeignKey('patronage.id')))


class Patronage(SqlAlchemyBase):
    __tablename__ = 'patronage'

    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True,
                           primary_key=True)
    chat_id = sqlalchemy.Column(sqlalchemy.Integer)
    patient = orm.relation('Patient', secondary='patients_has_patronage',
                           back_populates='patronage')




