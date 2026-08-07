"""Tests for the APScheduler integration."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.scheduler import (
    JOB_ID,
    get_scheduler,
    setup_scheduler,
    shutdown_scheduler,
)


@pytest.fixture(autouse=True)
def _cleanup_scheduler():
    """Ensure scheduler is shut down after each test."""
    yield
    shutdown_scheduler()


def test_setup_scheduler_without_api_key():
    """Scheduler should not start when ANTHROPIC_API_KEY is missing."""
    with patch.dict("os.environ", {}, clear=True):
        result = setup_scheduler()

    assert result is None
    assert get_scheduler() is None


@pytest.mark.asyncio
async def test_setup_scheduler_with_api_key():
    """Scheduler should start and register the daily job when key is set."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        scheduler = setup_scheduler()

    assert scheduler is not None
    assert get_scheduler() is scheduler
    job = scheduler.get_job(JOB_ID)
    assert job is not None


@pytest.mark.asyncio
async def test_shutdown_scheduler():
    """shutdown_scheduler should stop the scheduler and clear the reference."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        setup_scheduler()

    assert get_scheduler() is not None
    shutdown_scheduler()
    assert get_scheduler() is None


def test_shutdown_scheduler_when_not_running():
    """shutdown_scheduler should be safe to call when no scheduler exists."""
    shutdown_scheduler()  # should not raise


@pytest.mark.asyncio
async def test_job_trigger_config():
    """The daily job should be configured with 4:30 PM ET cron trigger."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        scheduler = setup_scheduler()

    job = scheduler.get_job(JOB_ID)
    trigger = job.trigger
    # CronTrigger fields list — check hour and minute
    fields = {f.name: str(f) for f in trigger.fields}
    assert fields["hour"] == "16"
    assert fields["minute"] == "30"
