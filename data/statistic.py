import sqlalchemy
from .db_session import SqlAlchemyBase


class Statistic(SqlAlchemyBase):
    __tablename__ = 'statistic'

    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True)
    user_code = sqlalchemy.Column(sqlalchemy.String(45), primary_key=True,
                                  unique=True)
    accept_time_first = sqlalchemy.Column(sqlalchemy.Time)
    accept_time_second = sqlalchemy.Column(sqlalchemy.Time)
    sys_press = sqlalchemy.Column(sqlalchemy.Integer)
    dias_press = sqlalchemy.Column(sqlalchemy.Integer)
    heart_rate = sqlalchemy.Column(sqlalchemy.Integer)



