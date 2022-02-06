from data import db_session
from data.patient import Patient
from data.patronage import Patronage
from data.accept_time import AcceptTime
from data.record import Record
from typing import Any
import pandas as pd


def create_session():
    db_session.global_init()
    return db_session.create_session()


db_sess = create_session()


def add_accept_time(time, patient: Patient) -> int:
    accept_time = AcceptTime(time=time, patient=patient)
    db_sess.add(accept_time)
    db_sess.commit()
    return accept_time.id


def get_accept_time_by_patient(patient: Patient):
    dbs = create_session()
    res = dbs.query(AcceptTime).filter(
        AcceptTime.patient_id == patient.id).all()
    dbs.close()
    return res


def add_patient(time_morn, time_even, **kwargs: Any):
    global db_sess
    with create_session() as db_sess:
        patient = Patient(**kwargs)
        db_sess.add(patient)
        db_sess.commit()
        return {'MOR': add_accept_time(time_morn, patient),
                'EVE': add_accept_time(time_even, patient)}


def get_patient_by_chat_id(chat_id: int) -> Patient:
    with create_session() as dbs:
        return dbs.query(Patient).filter(Patient.chat_id == chat_id).first()


def get_patient_by_user_code(user_code: str) -> Patient:
    return db_sess.query(Patient).filter(Patient.user_code == user_code).first()


def get_all_patients() -> list:
    dbc = create_session()
    res = dbc.query(Patient).all()
    dbc.close()
    return res


def change_patients_time_zone(chat_id: int, time_zone: int) -> None:
    dbs = create_session()
    patient = get_patient_by_chat_id(chat_id)
    patient.time_zone = time_zone
    dbs.add(patient)
    dbs.commit()
    dbs.close()


def change_accept_time(accept_time_id, time):
    dbs = create_session()
    accept_time = dbs.query(AcceptTime).filter(AcceptTime.id == accept_time_id).first()
    accept_time.time = time
    dbs.add(accept_time)
    dbs.commit()
    dbs.close()


def change_patients_membership(chat_id: int, member: bool) -> None:
    patient = get_patient_by_chat_id(chat_id)
    patient.member = member
    db_sess.commit()


def add_patronage(**kwargs: Any) -> None:
    dbs = create_session()
    patronage = Patronage(**kwargs)
    dbs.add(patronage)
    dbs.commit()
    dbs.close()


def get_all_patronages():
    with create_session() as dbs:
        return dbs.query(Patronage).all()


def get_patronage_by_chat_id(chat_id: int) -> Patronage:
    with create_session() as dbs:
        return dbs.query(Patronage).filter(Patronage.chat_id == chat_id).first()


def add_record(**kwargs: Any) -> None:
    dbs = create_session()
    record = Record(**kwargs)
    dbs.add(record)
    dbs.commit()
    dbs.close()


def get_last_record_by_accept_time(accept_time_id):
    dbs = create_session()
    last_record = dbs.query(Record).filter(
        Record.accept_time_id == accept_time_id).all()
    dbs.close()
    return last_record

# def make_file_by_patient(patient):
#     arr_sys_press, arr_dias_press, arr_heart_rate, arr_time, arr_time_zone, \
#     arr_id = [], [], [], [], [], []
#     for accept_time in patient.accept_time:
#         for record in accept_time.record:
#             arr_sys_press.append(record.sys_press)
#             arr_dias_press.append(record.dias_press)
#             arr_heart_rate.append(record.heart_rate)
#             arr_time.append(record.time)
#             arr_time_zone.append(record.time_zone)
#     df = pd.DataFrame({'Систолическое давление': arr_sys_press,
#                        'Диастолическое давление': arr_dias_press,
#                        'Частота сердечных сокращений': arr_heart_rate,
#                        'Время приема таблеток и измерений': arr_time,
#                        'Часовой пояс': arr_time_zone})
#     df.to_excel('static/' + patient.user_code + '.xlsx')
    # accept_time = db_sess.query(AcceptTime).filter(
    #     AcceptTime == patient.accept_time).all()
    # print(accept_time)
    # response = db_sess.query(Record).filter(Record.accept_time == accept_time)
    # print(response)

