from db_api import *
from time import strptime


def main() -> None:
    # add_patient(strptime('8:00', '%H:%M'), name='Ivanov Ivan Ivanovich',
    #             user_code=122, time_zone=3, chat_id=394)
    # patient = get_patient_by_chat_id(370)
    print(get_all_patients())



if __name__ == "__main__":
    main()
