from db_api import *


def main() -> None:
    # add_patient(strptime('8:00', '%H:%M'), strptime('20:00', '%H:%M'),
    # name='Ivanov Ivan Ivanovich',
    #             user_code=122, time_zone=3, chat_id=394)
    # accept_times = get_accept_times_by_patient_id(4)
    # add_record(accept_times[1], time=accept_times[0].time, sys_press=120,
    #            dias_press=80, heart_rate=90,
    #            time_zone=accept_times[0].patient.id,
    #            accept_time_id=accept_times[1].id)
    # add_patronage(chat_id=123)
    # print(get_patient_by_chat_id('0'))
    # print(get_all_patients())
    # PatronageUser.make_file_patients()
    # make_file_patients()
    # create_session()
    # get_all_patients_v2()
    # patient = get_patient_by_chat_id(721698752)
    # with db_session.create_session() as db:
    #     print(patient.accept_time)
    # with db_session.create_session() as db:
    #     patient = db.query(Patient).filter(Patient.id == 34).first()
    #     print(patient.accept_time)
    # print(patient_exists_by_user_code('ASD'))
    # add_record(time=time.strptime('8:00', '%H:%M'), sys_press=120,
    # dias_press=80,
    #            heart_rate=90, time_zone=3,
    #            response_time=time.strptime('8:02', '%H:%M'),
    #            comment='custom', accept_time_id=184)
    # make_file_patients()
    make_patient_list()


if __name__ == "__main__":
    main()
