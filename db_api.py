from data import db_session
from data.patient import Patient
from data.patronage import Patronage
from data.accept_time import AcceptTime
from data.record import Record
from typing import Any
import pandas as pd


db_session.global_init()


def create_session():
    db_sess = db_session.create_session()
    db_sess.commit()
    db_sess.close()


def get_accept_times_by_patient_id(id: int):
    with db_session.create_session() as db_sess:
        return db_sess.query(AcceptTime).filter(AcceptTime.patient_id == id).all()


def add_accept_time(time, patient: Patient) -> None:
    with db_session.create_session() as db_sess:
        accept_time = AcceptTime(time=time, patient=patient)
        db_sess.add(accept_time)
        db_sess.commit()
    return accept_time.id



def add_patient(time_morn, time_even, **kwargs: Any):
    with db_session.create_session() as db_sess:
        patient = Patient(**kwargs)
        db_sess.add(patient)
        db_sess.commit()
        return {'MOR': add_accept_time(time_morn, patient),
                'EVE': add_accept_time(time_even, patient)}


def get_patient_by_chat_id(chat_id: int) -> Patient:
    with db_session.create_session() as db_sess:
        return db_sess.query(Patient).filter(Patient.chat_id == chat_id).first()


def get_patient_by_user_code(user_code: str) -> Patient:
    with db_session.create_session() as db_sess:
        return db_sess.query(Patient).filter(Patient.user_code == user_code).first()


def get_all_patients() -> list:
    with db_session.create_session() as db_sess:
        return db_sess.query(Patient).all()


def del_patient(id):
    with db_session.create_session() as db_sess:
        patient = db_sess.query(Patient).filter_by(id=id).first()
        for accept_time in patient.accept_time:
            for record in accept_time.record:
                db_sess.delete(record)
            db_sess.delete(accept_time)
        db_sess.delete(patient)
        db_sess.commit()

def change_patients_time_zone(chat_id: int, time_zone: int) -> None:
    with db_session.create_session() as db_sess:
        patient = get_patient_by_chat_id(chat_id)
        patient.time_zone = time_zone
        db_sess.add(patient)
        db_sess.commit()


def change_accept_time(accept_time_id, time):
    with db_session.create_session() as db_sess:
        accept_time = db_sess.query(AcceptTime).filter(AcceptTime.id == accept_time_id).first()
        accept_time.time = time
        db_sess.add(accept_time)
        db_sess.commit()


def change_patients_membership(chat_id: int, member: bool) -> None:
    with db_session.create_session() as db_sess:
        patient = get_patient_by_chat_id(chat_id)
        patient.member = member
        db_sess.add(patient)
        db_sess.commit()


def add_patronage(**kwargs: Any) -> None:
    with db_session.create_session() as db_sess:
        patronage = Patronage(**kwargs)
        db_sess.add(patronage)
        db_sess.commit()


def get_all_patronages():
    with create_session() as dbs:
        return dbs.query(Patronage).all()


def get_patronage_by_chat_id(chat_id: int) -> Patronage:
    with db_session.create_session() as db_sess:
        return db_sess.query(Patronage).filter(Patronage.chat_id
                                               == chat_id).first()


def add_record(accept_time, **kwargs: Any) -> None:
    with db_session.create_session() as db_sess:
        record = Record(**kwargs)
        db_sess.add(record)
        db_sess.commit()


def get_last_record_by_accept_time(accept_time_id):
    with db_session.create_session() as db_sess:
        last_record = db_sess.query(Record).filter(
            Record.accept_time_id == accept_time_id).all()
        return last_record


def make_file_by_patient(id):
    with db_session.create_session() as db_sess:
        records = db_sess.query(Record).join(AcceptTime).join(
            Patient).filter(Patient.id == id).all()
        arr_sys_press, arr_dias_press, arr_heart_rate, arr_time, arr_time_zone, \
        arr_id = [], [], [], [], [], []
        for record in records:
            arr_sys_press.append(record.sys_press)
            arr_dias_press.append(record.dias_press)
            arr_heart_rate.append(record.heart_rate)
            arr_time.append(record.time)
            arr_time_zone.append(record.time_zone)
        df = pd.DataFrame({'Систолическое давление': arr_sys_press,
                           'Диастолическое давление': arr_dias_press,
                           'Частота сердечных сокращений': arr_heart_rate,
                           'Время приема таблеток и измерений': arr_time,
                           'Часовой пояс': arr_time_zone})
        df.to_excel('static/' + str(id) + '.xlsx')


def make_file_patients():
    arr_sys_press, arr_dias_press, arr_heart_rate, arr_time, arr_time_zone, \
    arr_patient_user_code, arr_patient_id = [], [], [], [], [], [], []
    # alias = Patient.query().join(AcceptTime,
    #         Patient.id == AcceptTime.patient_id).join(Record, AcceptTime.record == Record.accept_time_id).all()
    # print(alias)
    # for record in records:
    #     arr_patient_id.append(patient.id)
    #     arr_patient_user_code.append(patient.user_code)
    #     arr_sys_press.append(record.sys_press)
    #     arr_dias_press.append(record.dias_press)
    #     arr_heart_rate.append(record.heart_rate)
    #     arr_time.append(record.time)
    #     arr_time_zone.append(record.time_zone)
    # df = DataFrame({'ID пациента': arr_patient_id,
    #                 'Код пациента': arr_patient_user_code,
    #                 'Систолическое давление': arr_sys_press,
    #                 'Диастолическое давление': arr_dias_press,
    #                 'Частота сердечных сокращений': arr_heart_rate,
    #                 'Время приема таблеток и измерений': arr_time,
    #                 'Часовой пояс': arr_time_zone})
    # df.to_excel(f'static/statistics.xlsx')

