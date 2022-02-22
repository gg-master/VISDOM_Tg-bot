import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Doctor(SqlAlchemyBase):
    __tablename__ = 'doctor'

    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True,
                           primary_key=True)
    chat_id = sqlalchemy.Column(sqlalchemy.Integer)
    doctor_code = sqlalchemy.Column(sqlalchemy.String(4))
    patient = orm.relation('Patient', back_populates='doctor',
                           passive_deletes='all')
    region = orm.relation('Region')

    def __repr__(self):
        return f'Doctor: {self.chat_id} {self.doctor_code}'




