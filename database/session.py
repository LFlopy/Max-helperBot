from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import DATABASE_URL, SQLALCHEMY_ECHO


engine = create_async_engine(
    DATABASE_URL,
    echo=SQLALCHEMY_ECHO,
)

session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
