import sqlalchemy
from .db_session import SqlAlchemyBase


class Patient(SqlAlchemyBase):
    __tablename__ = 'patients'

    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String(45))
    user_code = sqlalchemy.Column(sqlalchemy.String(45), primary_key=True,
                                  unique=True)
    medicines = sqlalchemy.Column(sqlalchemy.String(45))
    accept_time_first = sqlalchemy.Column(sqlalchemy.Time)
    accept_time_second = sqlalchemy.Column(sqlalchemy.Time)
    diff_time = sqlalchemy.Column(sqlalchemy.Integer)
    chat_id = sqlalchemy.Column(sqlalchemy.String(45))
    member = sqlalchemy.Column(sqlalchemy.Boolean)


