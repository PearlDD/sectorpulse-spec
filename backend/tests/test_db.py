import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.crud import create_report, get_latest_report, get_report_by_id, get_reports
from app.db.models import Base


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def _sample_report(**overrides) -> dict:
    data = {
        "trigger": "manual",
        "cycle_phase": "expansion",
        "cycle_confidence": 0.85,
        "risk_level": "moderate",
        "narrative": "Markets are expanding steadily.",
        "sector_scores": {"XLK": 82, "XLF": 71},
        "allocation": {"XLK": 0.4, "XLF": 0.3, "cash": 0.3},
        "rrg_data": {"XLK": {"rs_ratio": 102, "rs_momentum": 101}},
        "raw_macro_data": {"PMI": 55.2, "VIX": 14.5},
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_create_report(db_session: AsyncSession):
    report = await create_report(db_session, _sample_report())
    assert report.id is not None
    assert report.cycle_phase == "expansion"
    assert report.sector_scores == {"XLK": 82, "XLF": 71}


@pytest.mark.asyncio
async def test_get_reports_ordering(db_session: AsyncSession):
    await create_report(db_session, _sample_report(cycle_phase="expansion"))
    await create_report(db_session, _sample_report(cycle_phase="contraction"))

    reports = await get_reports(db_session)
    assert len(reports) == 2
    # Most recent first
    assert reports[0].cycle_phase == "contraction"
    assert reports[1].cycle_phase == "expansion"


@pytest.mark.asyncio
async def test_get_reports_limit_offset(db_session: AsyncSession):
    for i in range(5):
        await create_report(db_session, _sample_report(cycle_confidence=float(i)))

    page = await get_reports(db_session, limit=2, offset=2)
    assert len(page) == 2


@pytest.mark.asyncio
async def test_get_latest_report(db_session: AsyncSession):
    await create_report(db_session, _sample_report(risk_level="low"))
    await create_report(db_session, _sample_report(risk_level="high"))

    latest = await get_latest_report(db_session)
    assert latest is not None
    assert latest.risk_level == "high"


@pytest.mark.asyncio
async def test_get_latest_report_empty(db_session: AsyncSession):
    latest = await get_latest_report(db_session)
    assert latest is None


@pytest.mark.asyncio
async def test_get_report_by_id(db_session: AsyncSession):
    created = await create_report(db_session, _sample_report())
    found = await get_report_by_id(db_session, created.id)
    assert found is not None
    assert found.id == created.id
    assert found.narrative == "Markets are expanding steadily."


@pytest.mark.asyncio
async def test_get_report_by_id_not_found(db_session: AsyncSession):
    result = await get_report_by_id(db_session, 9999)
    assert result is None
