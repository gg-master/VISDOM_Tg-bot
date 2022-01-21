import os
import sqlalchemy as sa
import sqlalchemy.orm as orm
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import sqlalchemy.ext.declarative as dec
import logging
from sqlalchemy.pool import NullPool
from tools.tools import get_from_env


SqlAlchemyBase = dec.declarative_base()


__factory = None


def global_init():
    global __factory

    if __factory:
        return
    os.chdir('..')
    db_address = get_from_env('DB_ADDRESS')
    # if os.path.exists(path):
    #     load_dotenv(path)
    # try:
    #     db_address = os.environ.get('DB_ADDRESS')
    #     if db_address is None:
    #         raise AttributeError("param DB_PASS is 'NoneType'")
    # except Exception as ex:
    #     logging.error(f'Probably not found .env file'
    #                   f'\nEXCEPTION: {ex}')
    #     return None

    conn_str = db_address
    # print(f"Подключение к базе данных по адресу {conn_str}")
    logging.info(f"Подключение к базе данных по адресу {conn_str}")
    engine = sa.create_engine(conn_str, echo=False, poolclass=NullPool)
    __factory = orm.sessionmaker(bind=engine)

    import __all_models

    SqlAlchemyBase.metadata.create_all(engine)


def create_session() -> Session:
    global __factory
    return __factory()
