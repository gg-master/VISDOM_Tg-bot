import logging

import sqlalchemy as sa
import sqlalchemy.ext.declarative as dec
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from tools.tools import get_from_env

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')

SqlAlchemyBase = dec.declarative_base()


__factory = None


def global_init():
    global __factory

    if __factory:
        return
    db_address = get_from_env('DB_ADDRESS')

    conn_str = db_address

    logging.info(f"Подключение к базе данных по адресу {conn_str}")
    engine = sa.create_engine(conn_str, echo=False, poolclass=NullPool)
    __factory = orm.sessionmaker(bind=engine, expire_on_commit=False)

    from . import __all_models

    SqlAlchemyBase.metadata.create_all(engine)


def create_session() -> Session:
    global __factory
    return __factory()
