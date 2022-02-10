import csv
from typing import Any

from openpyxl import Workbook, styles

from data import db_session
from data.accept_time import AcceptTime
from data.patient import Patient
from data.patronage import Patronage
from data.record import Record

db_session.global_init()


def create_session():
    db_sess = db_session.create_session()
    db_sess.commit()
    db_sess.close()


def get_accept_times_by_patient_id(p_id: int):
    with db_session.create_session() as db_sess:
        return db_sess.query(AcceptTime).filter(
            AcceptTime.patient_id == p_id).all()


def add_accept_time(time, patient: Patient) -> int:
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
        return db_sess.query(Patient).filter(
            Patient.chat_id == chat_id).first()


def get_patient_by_user_code(user_code: str) -> Patient:
    with db_session.create_session() as db_sess:
        return db_sess.query(Patient).filter(
            Patient.user_code == user_code).first()


def get_all_patients() -> list:
    with db_session.create_session() as db_sess:
        return db_sess.query(Patient).all()


def del_patient(p_id):
    with db_session.create_session() as db_sess:
        patient = db_sess.query(Patient).filter_by(id=p_id).first()
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
        accept_time = db_sess.query(AcceptTime).filter(AcceptTime.id ==
                                                       accept_time_id).first()
        accept_time.time = time
        db_sess.add(accept_time)
        db_sess.commit()


def change_patients_membership(user_code: str, member: bool) -> None:
    with db_session.create_session() as db_sess:
        patient = get_patient_by_user_code(user_code)
        patient.member = member
        db_sess.add(patient)
        db_sess.commit()


def patient_exists_by_user_code(user_code):
    with db_session.create_session() as db_sess:
        return db_sess.query(db_sess.query(Patient).filter(
            Patient.user_code == user_code).exists()).scalar()


def add_patronage(**kwargs: Any) -> None:
    with db_session.create_session() as db_sess:
        patronage = Patronage(**kwargs)
        db_sess.add(patronage)
        db_sess.commit()


def get_all_patronages():
    with db_session.create_session() as db_sess:
        return db_sess.query(Patronage).all()


def get_patronage_by_chat_id(chat_id: int) -> Patronage:
    with db_session.create_session() as db_sess:
        return db_sess.query(Patronage).filter(Patronage.chat_id
                                               == chat_id).first()


def add_record(**kwargs: Any) -> None:
    with db_session.create_session() as db_sess:
        record = Record(**kwargs)
        db_sess.add(record)
        db_sess.commit()


def get_last_record_by_accept_time(accept_time_id):
    with db_session.create_session() as db_sess:
        records = db_sess.query(Record).filter(
            Record.accept_time_id == accept_time_id,
            Record.sys_press != None).all()
        return records


def get_all_records_by_accept_time(accept_time_id):
    with db_session.create_session() as db_sess:
        records = db_sess.query(Record).filter(
            Record.accept_time_id == accept_time_id).all()
        return records


def make_file_by_patient_user_code(user_code):
    with db_session.create_session() as db_sess:
        records = db_sess.execute(f"""SELECT record.sys_press,
                  record.dias_press, record.heart_rate, record.time,
                  record.time_zone, record.response_time, record.comment FROM
                  patient JOIN accept_time on patient.id = 
                  accept_time.Patient_id JOIN record on accept_time.id = 
                  record.accept_time_id WHERE patient.user_code like 
                  '{user_code}'""")
    headers = ['Систолическое давление', 'Диастолическое давление',
               'Частота сердечных сокращений',
               'Время приема таблеток и измерений', 'Часовой пояс',
               'Время ответа', 'Комментарий']
    wb = Workbook()
    ws = wb.active
    for i in range(len(headers)):
        ws.cell(row=1, column=i + 1, value=headers[i])
    i = 2
    for record in records:
        for j in range(7):
            ws.cell(row=i, column=j + 1, value=record[j])
        i += 1
    wb.save(filename=f'static/{user_code}_data.xlsx')


def make_file_patients():
    with db_session.create_session() as db_sess:
        records = db_sess.execute('SELECT patient.id, patient.user_code,'
                                  ' record.sys_press, record.dias_press,'
                                  ' record.heart_rate, record.time, record.'
                                  'time_zone, record.response_time,'
                                  ' record.comment FROM patient JOIN'
                                  ' accept_time on patient.id = accept_time.'
                                  'Patient_id JOIN record on accept_time.id'
                                  ' = record.accept_time_id')
    # wb = Workbook()
    # ws = wb.active
    headers = ['ID пациента', 'Код пациента', 'Систолическое давление',
               'Диастолическое давление', 'Частота сердечных сокращений',
               'Время приема таблеток и измерений', 'Часовой пояс',
               'Время ответа', 'Комментарий']
    with open('static/statistics.csv', 'w', encoding='utf-8', newline='') as \
            csvfile:
        writer = csv.writer(csvfile, delimiter=';', quotechar='"',
                            quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        for record in records:
            writer.writerow(record)
    # for i in range(len(headers)):
    #     ws.cell(row=1, column=i + 1, value=headers[i])
    # i = 2
    # for record in records:
    #     for j in range(9):
    #         ws.cell(row=i, column=j+1, value=record[j])
    #     i += 1
    # wb.save(filename='static/statistics.xlsx')


def get_all_patients_v2():
    dct = {}
    with db_session.create_session() as db_sess:
        patients = db_sess.query(Patient, AcceptTime.time).join(
            AcceptTime).group_by(Patient.id, AcceptTime.time).all()
        for patient in patients:
            if patient[0] not in dict:
                dct[patient[0]] = [patient[1]]
            else:
                dct[patient[0]].append(patient[1])
        print(list(dct.items()))


def make_patient_list():
    with db_session.create_session() as db_sess:
        patients_user_codes = db_sess.query(Patient.user_code,
                                            Patient.member).all()
    wb = Workbook()
    ws = wb.active
    for i in range(len(patients_user_codes)):
        cell = ws.cell(row=i + 1, column=1, value=patients_user_codes[i][0])
        if not patients_user_codes[i][1]:
            cell.fill = styles.PatternFill('solid', fgColor='FF0000')
    wb.save(filename=f'static/Список пациентов.xlsx')
