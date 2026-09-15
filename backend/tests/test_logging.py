"""Tests for structured logging and request ID middleware."""

import json
import logging

from starlette.testclient import TestClient

from app.logging_config import JsonFormatter, request_id_var
from app.main import app


client = TestClient(app)


class TestRequestIDMiddleware:
    def test_health_returns_200(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_response_has_request_id_header(self):
        response = client.get("/api/health")
        rid = response.headers.get("x-request-id")
        assert rid is not None
        assert len(rid) > 0

    def test_respects_incoming_request_id(self):
        custom_id = "test-request-id-12345"
        response = client.get(
            "/api/health", headers={"x-request-id": custom_id}
        )
        assert response.headers.get("x-request-id") == custom_id


class TestJsonFormatter:
    def test_formatter_outputs_valid_json_with_all_fields(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        token = request_id_var.set("test-rid-abc")
        try:
            output = formatter.format(record)
            parsed = json.loads(output)
            assert parsed["level"] == "INFO"
            assert parsed["logger"] == "test.logger"
            assert parsed["message"] == "test message"
            assert parsed["request_id"] == "test-rid-abc"
            assert "timestamp" in parsed
        finally:
            request_id_var.reset(token)

    def test_formatter_request_id_is_none_without_context(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="",
            lineno=0, msg="no context", args=(), exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        assert parsed["request_id"] is None
