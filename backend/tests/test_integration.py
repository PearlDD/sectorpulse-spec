"""Integration tests — end-to-end API flows with a test database."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agents.macro_analyst import CyclePhase
from app.agents.narrative_gen import NarrativeReport
from app.agents.orchestrator import AnalysisResult
from app.agents.portfolio_allocator import PortfolioAllocation
from app.agents.sector_analyst import SectorAnalysis, SectorScore
from app.api.routes import _rate_limit_state
from app.db.database import get_db
from app.db.models import Base
from app.main import app


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _rate_limit_state["date"] = None
    _rate_limit_state["count"] = 0


def _fake_result() -> AnalysisResult:
    return AnalysisResult(
        trigger="manual",
        cycle_phase=CyclePhase(
            phase="expansion",
            confidence=0.85,
            reasoning="PMI above 50",
            risk_level="moderate",
        ),
        sector_analysis=SectorAnalysis(
            sectors=[
                SectorScore(ticker="XLK", score=82.0, reasoning="Tech leads"),
                SectorScore(ticker="XLF", score=71.0, reasoning="Financials solid"),
            ]
        ),
        allocation=PortfolioAllocation(
            weights={"XLK": 0.4, "XLF": 0.3, "cash": 0.3},
            reasoning="Overweight tech",
        ),
        narrative=NarrativeReport(
            market_narrative="Economy expanding steadily.",
            sector_explanations={"XLK": "Strong growth", "XLF": "Rate tailwind"},
        ),
        rrg_data={"XLK": {"rs_ratio": 102, "rs_momentum": 101}},
        macro_snapshot={"PMI": 55.2},
    )


# --------------------------------------------------------------------------- #
# Integration test: health
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# --------------------------------------------------------------------------- #
# Integration test: POST /api/run with mocked orchestrator
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_run_with_mocked_orchestrator(client: AsyncClient):
    with patch("app.api.routes.run_analysis", new_callable=AsyncMock) as mock:
        mock.return_value = _fake_result()
        resp = await client.post("/api/run")
    assert resp.status_code == 201
    data = resp.json()
    assert data["cycle_phase"] == "expansion"
    assert data["id"] is not None


# --------------------------------------------------------------------------- #
# Integration test: GET /api/reports returns list after creating a report
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_reports_list_after_creation(client: AsyncClient):
    with patch("app.api.routes.run_analysis", new_callable=AsyncMock) as mock:
        mock.return_value = _fake_result()
        await client.post("/api/run")

    resp = await client.get("/api/reports")
    assert resp.status_code == 200
    reports = resp.json()
    assert len(reports) == 1
    assert reports[0]["cycle_phase"] == "expansion"


# --------------------------------------------------------------------------- #
# Integration test: GET /api/reports/latest returns the created report
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_reports_latest_returns_created_report(client: AsyncClient):
    with patch("app.api.routes.run_analysis", new_callable=AsyncMock) as mock:
        mock.return_value = _fake_result()
        await client.post("/api/run")

    resp = await client.get("/api/reports/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["narrative"] == "Economy expanding steadily."
    assert data["cycle_phase"] == "expansion"


# --------------------------------------------------------------------------- #
# Integration test: GET /api/reports/{id} returns the specific report
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_report_by_id(client: AsyncClient):
    with patch("app.api.routes.run_analysis", new_callable=AsyncMock) as mock:
        mock.return_value = _fake_result()
        resp = await client.post("/api/run")
    report_id = resp.json()["id"]

    resp = await client.get(f"/api/reports/{report_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == report_id


# --------------------------------------------------------------------------- #
# Integration test: GET /api/reports/{id} with invalid id returns 404
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_report_invalid_id_returns_404(client: AsyncClient):
    resp = await client.get("/api/reports/99999")
    assert resp.status_code == 404
