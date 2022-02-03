from db_api import *
from time import strptime
import pandas as pd





def main() -> None:
    # add_patient(strptime('8:00', '%H:%M'), strptime('20:00', '%H:%M'), name='Ivanov Ivan Ivanovich',
    #             user_code=122, time_zone=3, chat_id=394)
    # add_patronage(chat_id=123)
    print(get_patient_by_chat_id('0'))
    # print(get_all_patients())



if __name__ == "__main__":
    main()
