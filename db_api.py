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
    dbs = create_session()
    accept_time = AcceptTime(time=time, patient=patient)
    dbs.add(accept_time)
    dbs.commit()
    dbs.close()
    return accept_time.id


def get_accept_time_by_patient(patient: Patient):
    dbs = create_session()
    res = dbs.query(AcceptTime).filter(
        AcceptTime.patient_id == patient.id).all()
    dbs.close()
    return res


def add_patient(time_morn, time_even, **kwargs: Any):
    dbs = create_session()
    patient = Patient(**kwargs)
    dbs.add(patient)
    dbs.commit()
    res = {'MOR': add_accept_time(time_morn, patient),
           'EVE': add_accept_time(time_even, patient)}
    dbs.close()
    return res


def get_patient_by_chat_id(chat_id: int) -> Patient:
    dbs = create_session()
    res = dbs.query(Patient).filter(Patient.chat_id == chat_id).first()
    dbs.close()
    return res


def get_patient_by_user_code(user_code: str) -> Patient:
    return db_sess.query(Patient).filter(Patient.user_code == user_code).first()


def get_all_patients() -> list:
    dbc = create_session()
    res = dbc.query(Patient).all()
    dbc.close()
    return res


def change_patients_time_zone(chat_id: int, time_zone: int) -> None:
    patient = get_patient_by_chat_id(chat_id)
    patient.time_zone = time_zone
    db_sess.commit()


def change_patients_membership(chat_id: int, member: bool) -> None:
    patient = get_patient_by_chat_id(chat_id)
    patient.member = member
    db_sess.commit()


def add_patronage(**kwargs: Any) -> None:
    patronage = Patronage(**kwargs)
    db_sess.add(patronage)
    db_sess.commit()


def get_patronage_by_chat_id(chat_id: int) -> Patronage:
    return db_sess.query(Patronage).filter(Patronage.chat_id == chat_id).first()


def add_record(**kwargs: Any) -> None:
    dbs = create_session()
    record = Record(**kwargs)
    dbs.add(record)
    dbs.commit()
    dbs.close()

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
