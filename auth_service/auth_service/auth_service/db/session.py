import time

from asyncpg_utils.databases import Database
from loguru import logger
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, DeclarativeMeta

from auth_service.core.config import get_app_settings

engine: AsyncEngine = create_async_engine(
    get_app_settings().postgres_asyncpg_dsn
)


Base: DeclarativeMeta = declarative_base()
Base.metadata.bind = engine

SessionLocal = sessionmaker(  # noqa
    engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

pg_database = Database(get_app_settings().raw_postgres_dsn)


# noinspection PyUnusedLocal
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(
    conn, cursor, statement, parameters, context, executemany
):  # noqa
    conn.info.setdefault("query_start_time", []).append(time.time())
    logger.debug(
        f"Start Query: {statement}",
    )


# noinspection PyUnusedLocal
@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(
    conn, cursor, statement, parameters, context, executemany
):  # noqa
    total = time.time() - conn.info["query_start_time"].pop(-1)
    logger.debug("Query Complete!")
    logger.debug(f"Total Time: {total:0.4f}")
