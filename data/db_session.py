import os
import sqlalchemy as sa
import sqlalchemy.orm as orm
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import sqlalchemy.ext.declarative as dec
import logging
from sqlalchemy.pool import NullPool


SqlAlchemyBase = dec.declarative_base()


__factory = None


def global_init():
    global __factory

    if __factory:
        return

    # if not db_file or not db_file.strip():
    #     raise Exception("Необходимо указать файл базы данных.")
    #
    # path = os.path.join(os.path.dirname(__package__), '.env')
    # if os.path.exists(path):
    #     load_dotenv(path)
    # try:
    #     db_pass = os.environ.get('DB_PASS')
    #     if db_pass is None:
    #         raise AttributeError("param DB_PASS is 'NoneType'")
    # except Exception as ex:
    #     logging.error(f'Probably not found .env file'
    #                   f'\nEXCEPTION: {ex}')
    #     return None
    conn_str = f'mysql+pymysql://root:BENQgw2270@127.0.0.1:3306/my_db_visdom'
    # print(f"Подключение к базе данных по адресу {conn_str}")
    logging.info(f"Подключение к базе данных по адресу {conn_str}")
    engine = sa.create_engine(conn_str, echo=False, poolclass=NullPool)
    __factory = orm.sessionmaker(bind=engine)

    # from . import __all_models

    SqlAlchemyBase.metadata.create_all(engine)


def create_session() -> Session:
    global __factory
    return __factory()
