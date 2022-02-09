import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class AcceptTime(SqlAlchemyBase):
    __tablename__ = 'accept_time'

    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True,
                           primary_key=True)
    patient_id = sqlalchemy.Column(sqlalchemy.Integer,
                                   sqlalchemy.ForeignKey('patient.id',
                                                         ondelete='CASCADE'))
    time = sqlalchemy.Column(sqlalchemy.Time)
    record = orm.relationship('Record', back_populates='accept_time',
                              passive_deletes='all')
    patient = orm.relation('Patient')

    def __repr__(self):
        return f'{self.patient_id} - {self.time}'

