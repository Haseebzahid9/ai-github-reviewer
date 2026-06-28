from __future__ import annotations

from datetime import datetime
import json
import os

from dotenv import load_dotenv
from sqlalchemy import String, Float, DateTime, Text, text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "sqlite+aiosqlite:///./github_reviewer.db"
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Report(Base):
    __tablename__ = "reports"

    id:               Mapped[int]      = mapped_column(primary_key=True, index=True)
    repo_url:         Mapped[str]      = mapped_column(String(500),  nullable=False)
    repo_name:        Mapped[str]      = mapped_column(String(200),  nullable=False)
    score:            Mapped[float]    = mapped_column(Float,        nullable=False)
    grade:            Mapped[str]      = mapped_column(String(4),    nullable=False, default="N/A")
    primary_language: Mapped[str]      = mapped_column(String(60),   nullable=False, default="")
    created_at:       Mapped[datetime] = mapped_column(DateTime,     default=datetime.utcnow)
    report_data:      Mapped[str]      = mapped_column(Text,         nullable=False)

    def report_data_as_dict(self) -> dict:
        return json.loads(self.report_data)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Safe additive migrations — ignore errors when columns already exist.
        # SQLite does not support IF NOT EXISTS in ALTER TABLE.
        _new_columns = [
            "ALTER TABLE reports ADD COLUMN grade TEXT NOT NULL DEFAULT 'N/A'",
            "ALTER TABLE reports ADD COLUMN primary_language TEXT NOT NULL DEFAULT ''",
        ]
        for stmt in _new_columns:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # Column already present — safe to ignore


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
