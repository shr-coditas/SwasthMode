from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


@lru_cache
def sessions() -> sessionmaker:
    engine = create_engine(
        settings().database_url.get_secret_value(), pool_pre_ping=True,
        pool_size=5, max_overflow=5, pool_timeout=5, hide_parameters=True,
        connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000"},
    )
    return sessionmaker(engine, expire_on_commit=False)
