import sqlalchemy
from data import db_session
import datetime
from data.patient import PatientModel


def main():
    db_session.global_init()



if __name__ == "__main__":
    main()
