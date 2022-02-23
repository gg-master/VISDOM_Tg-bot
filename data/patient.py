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
    time_zone = sqlalchemy.Column(sqlalchemy.String(45))
    chat_id = sqlalchemy.Column(sqlalchemy.Integer, unique=True)
    member = sqlalchemy.Column(sqlalchemy.Boolean, default=True)
    accept_time = orm.relation('AcceptTime', back_populates='patient',
                               passive_deletes='all')
    doctor_id = sqlalchemy.Column(sqlalchemy.Integer,
                                  sqlalchemy.ForeignKey('doctor.id',
                                                        ondelete='CASCADE'))
    doctor = orm.relationship('Doctor')

    def __repr__(self):
        return f'''Patient: {self.id, self.name, self.user_code, self.chat_id,
                             self.time_zone, self.member}'''
