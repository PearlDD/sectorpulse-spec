"""Tests for the FastAPI REST API routes."""

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
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _rate_limit_state["date"] = None
    _rate_limit_state["count"] = 0


def _mock_analysis_result() -> AnalysisResult:
    return AnalysisResult(
        trigger="manual",
        cycle_phase=CyclePhase(
            phase="expansion",
            confidence=0.85,
            reasoning="PMI strong",
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
            market_narrative="Markets are expanding steadily.",
            sector_explanations={"XLK": "Strong growth", "XLF": "Rate tailwind"},
        ),
        rrg_data={"XLK": {"rs_ratio": 102, "rs_momentum": 101}},
        macro_snapshot={"PMI": 55.2, "VIX": 14.5},
    )


@pytest.mark.asyncio
async def test_health_no_reports(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["last_run"] is None


@pytest.mark.asyncio
async def test_health_with_report(client: AsyncClient):
    with patch("app.api.routes.run_analysis", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = _mock_analysis_result()
        await client.post("/api/run")

    resp = await client.get("/api/health")
    data = resp.json()
    assert data["status"] == "ok"
    assert data["last_run"] is not None


@pytest.mark.asyncio
async def test_post_run_creates_report(client: AsyncClient):
    with patch("app.api.routes.run_analysis", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = _mock_analysis_result()
        resp = await client.post("/api/run")

    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["cycle_phase"] == "expansion"
    assert data["sector_scores"] == {"XLK": 82.0, "XLF": 71.0}
    assert data["allocation"] == {"XLK": 0.4, "XLF": 0.3, "cash": 0.3}


@pytest.mark.asyncio
async def test_get_reports_list(client: AsyncClient):
    with patch("app.api.routes.run_analysis", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = _mock_analysis_result()
        await client.post("/api/run")

    resp = await client.get("/api/reports")
    assert resp.status_code == 200
    reports = resp.json()
    assert len(reports) == 1
    assert reports[0]["cycle_phase"] == "expansion"
    # Summary should not include full fields like narrative
    assert "narrative" not in reports[0]


@pytest.mark.asyncio
async def test_get_reports_latest(client: AsyncClient):
    with patch("app.api.routes.run_analysis", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = _mock_analysis_result()
        await client.post("/api/run")

    resp = await client.get("/api/reports/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["narrative"] == "Markets are expanding steadily."


@pytest.mark.asyncio
async def test_get_reports_latest_empty(client: AsyncClient):
    resp = await client.get("/api/reports/latest")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_report_by_id(client: AsyncClient):
    with patch("app.api.routes.run_analysis", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = _mock_analysis_result()
        resp = await client.post("/api/run")
    report_id = resp.json()["id"]

    resp = await client.get(f"/api/reports/{report_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == report_id


@pytest.mark.asyncio
async def test_get_report_not_found(client: AsyncClient):
    resp = await client.get("/api/reports/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rate_limiting(client: AsyncClient):
    with patch("app.api.routes.run_analysis", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = _mock_analysis_result()

        for i in range(3):
            resp = await client.post("/api/run")
            assert resp.status_code == 201, f"Run {i+1} should succeed"

        resp = await client.post("/api/run")
        assert resp.status_code == 429


@pytest.mark.asyncio
async def test_sectors_endpoint(client: AsyncClient):
    with patch("app.api.routes.run_analysis", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = _mock_analysis_result()
        await client.post("/api/run")

    resp = await client.get("/api/sectors")
    assert resp.status_code == 200
    data = resp.json()
    assert "sector_scores" in data
    assert "allocation" in data
    assert data["sector_scores"]["XLK"] == 82.0


@pytest.mark.asyncio
async def test_sectors_rrg_endpoint(client: AsyncClient):
    with patch("app.api.routes.run_analysis", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = _mock_analysis_result()
        await client.post("/api/run")

    resp = await client.get("/api/sectors/rrg")
    assert resp.status_code == 200
    data = resp.json()
    assert "rrg_data" in data
    assert data["rrg_data"]["XLK"]["rs_ratio"] == 102


@pytest.mark.asyncio
async def test_sectors_empty(client: AsyncClient):
    resp = await client.get("/api/sectors")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sectors_rrg_empty(client: AsyncClient):
    resp = await client.get("/api/sectors/rrg")
    assert resp.status_code == 404
