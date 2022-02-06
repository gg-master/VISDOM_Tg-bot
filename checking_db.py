from db_api import *
from time import strptime
import pandas as pd
# from modules.users_classes import PatronageUser





def main() -> None:
    # add_patient(strptime('8:00', '%H:%M'), strptime('20:00', '%H:%M'), name='Ivanov Ivan Ivanovich',
    #             user_code=122, time_zone=3, chat_id=394)
    # accept_times = get_accept_times_by_patient_id(4)
    # add_record(accept_times[1], time=accept_times[0].time, sys_press=120,
    #            dias_press=80, heart_rate=90, time_zone=accept_times[0].patient.id,
    #            accept_time_id=accept_times[1].id)
    # add_patronage(chat_id=123)
    # print(get_patient_by_chat_id('0'))
    # print(get_all_patients())
    # PatronageUser.make_file_patients()
    # make_file_patients()
    create_session()




if __name__ == "__main__":
    main()
