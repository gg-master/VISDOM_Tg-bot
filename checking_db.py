import sqlalchemy
from data import db_session
import datetime
from data.patient import Patient


def main():
    db_session.global_init()
    patient = Patient()
    patient.name = 'Ivanov Ivan Semenovich'
    patient.user_code = 'IIS112'
    patient.medicines = 'some_drugs'
    patient.accept_time_first = datetime.time(hour=5)
    patient.accept_time_second = datetime.time(hour=17)
    patient.diff_time = 3
    patient.chat_id = 'random chat_id1'
    patient.member = True
    db_sess = db_session.create_session()
    db_sess.add(patient)
    db_sess.commit()


if __name__ == "__main__":
    main()
