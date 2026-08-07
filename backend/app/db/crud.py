from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Report


async def create_report(db: AsyncSession, report_data: dict) -> Report:
    report = Report(**report_data)
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def get_reports(
    db: AsyncSession, limit: int = 20, offset: int = 0
) -> list[Report]:
    stmt = (
        select(Report)
        .order_by(Report.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_latest_report(db: AsyncSession) -> Report | None:
    stmt = select(Report).order_by(Report.created_at.desc()).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_report_by_id(db: AsyncSession, report_id: int) -> Report | None:
    stmt = select(Report).where(Report.id == report_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
