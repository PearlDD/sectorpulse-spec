from datetime import datetime, timezone

from sqlalchemy import JSON, Integer, REAL, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )
    trigger: Mapped[str] = mapped_column(Text)
    cycle_phase: Mapped[str] = mapped_column(Text)
    cycle_confidence: Mapped[float] = mapped_column(REAL)
    risk_level: Mapped[str] = mapped_column(Text)
    narrative: Mapped[str] = mapped_column(Text)
    sector_scores: Mapped[dict] = mapped_column(JSON)
    allocation: Mapped[dict] = mapped_column(JSON)
    rrg_data: Mapped[dict] = mapped_column(JSON)
    raw_macro_data: Mapped[dict] = mapped_column(JSON)
