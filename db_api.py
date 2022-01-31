from data import db_session
from data.patient import Patient
from data.patronage import Patronage
from data.accept_time import AcceptTime
from data.record import Record
from typing import Any


def create_session():
    db_session.global_init()
    return db_session.create_session()


db_sess = create_session()


def add_accept_time(time, patient: Patient) -> None:
    accept_time = AcceptTime(time=time, patient=patient)
    db_sess.add(accept_time)
    db_sess.commit()


def add_patient(accept_time, **kwargs: Any) -> None:
    patient = Patient(**kwargs)
    db_sess.add(patient)
    db_sess.commit()
    add_accept_time(accept_time, patient)


def get_patient_by_chat_id(chat_id: int) -> Patient:
    return db_sess.query(Patient).filter(Patient.chat_id == chat_id).first()


def get_all_patients():
    return db_sess.query(Patient.chat_id, AcceptTime.time).join(AcceptTime).all()


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
    record = Record(**kwargs)
    db_sess.add(record)
    db_sess.commit()
