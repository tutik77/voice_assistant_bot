from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class UserValue(Base):
    __tablename__ = 'users_values'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    value = Column(String)

DATABASE_URL = 'postgresql+asyncpg://postgres:4276@127.0.0.1/users_values'
async_engine = create_async_engine(DATABASE_URL, echo=True, future=True, pool_size=10, max_overflow=20)
async_session = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)