from alembic import context
from sqlalchemy import create_engine, pool
from app.core.config import settings
from app.core.db.base import Base
from app.core.db import model_registry  # noqa: F401

url = settings().database_url.get_secret_value()

if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
