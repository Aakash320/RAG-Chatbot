"""
Comprehensive tests for the schedule service part of the app.
Covers:
- Schedule models, database operations, and validation (repository).
- Schedule MCP server tool endpoints.
- ScheduleService client integration and error wrapping.
- LangGraph scheduling nodes.
- ChatController and ChatSessionController schedule orchestration.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.exceptions import ScheduleError, WebSearchError
from app.core.mcp.external_client import ExternalMCPClient
from app.services.schedule_service import ScheduleService
from app.graph.nodes import (
    make_schedule_classification_node,
    make_schedule_add_node,
    make_schedule_list_node,
    _is_valid_date,
    _is_valid_time,
)
from app.controllers.chat_controller import ChatController
from app.controllers.chat_session_controller import ChatSessionController

from schedule_mcp_server.database import Base
from schedule_mcp_server.repository import ScheduleRepository, ScheduleValidationError
from schedule_mcp_server.models import Schedule
from schedule_mcp_server.server import add_schedule, list_schedules


# =====================================================================
# 1. DATABASE & REPOSITORY TESTS
# =====================================================================

@pytest.mark.anyio
async def test_schedule_repository_and_validation():
    # Set up in-memory sqlite engine
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        repo = ScheduleRepository(session)

        # A. Verify validation for helper functions
        assert _is_valid_date("2026-07-27") is True
        assert _is_valid_date("27-07-2026") is False
        assert _is_valid_date(None) is False
        assert _is_valid_time("14:30") is True
        assert _is_valid_time("25:00") is False
        assert _is_valid_time(None) is False

        # B. Test successful add
        record = await repo.add(
            user_id="user_123",
            description="Dentist appointment",
            date="2026-08-01",
            time="14:00"
        )
        assert record.id is not None
        assert record.user_id == "user_123"
        assert record.description == "Dentist appointment"
        assert record.date == "2026-08-01"
        assert record.time == "14:00"
        assert record.created_at is not None

        # C. Test validation failures
        # Invalid date format
        with pytest.raises(ScheduleValidationError) as exc:
            await repo.add(user_id="user_123", description="Meeting", date="2026/08/01", time="14:00")
        assert "date must be in YYYY-MM-DD format" in str(exc.value)

        # Non-existent calendar date
        with pytest.raises(ScheduleValidationError) as exc:
            await repo.add(user_id="user_123", description="Meeting", date="2026-02-31", time="14:00")
        assert "date is not a real calendar date" in str(exc.value)

        # Invalid time format
        with pytest.raises(ScheduleValidationError) as exc:
            await repo.add(user_id="user_123", description="Meeting", date="2026-08-01", time="2 PM")
        assert "time must be in 24-hour HH:MM format" in str(exc.value)

        # Empty description
        with pytest.raises(ScheduleValidationError) as exc:
            await repo.add(user_id="user_123", description="   ", date="2026-08-01", time="14:00")
        assert "description must not be empty" in str(exc.value)

        # D. Test list_for_user
        # Insert another schedule
        await repo.add(
            user_id="user_123",
            description="Gym session",
            date="2026-08-01",
            time="08:00"
        )
        # Insert schedule for a different user
        await repo.add(
            user_id="user_456",
            description="Lunch with Alice",
            date="2026-08-01",
            time="12:00"
        )

        # Fetch and verify list ordering
        records = await repo.list_for_user(user_id="user_123")
        assert len(records) == 2
        # Ordering is date, time
        assert records[0].description == "Gym session"  # 08:00
        assert records[1].description == "Dentist appointment"  # 14:00

        # Filter by date
        records_aug1 = await repo.list_for_user(user_id="user_123", date="2026-08-01")
        assert len(records_aug1) == 2
        records_aug2 = await repo.list_for_user(user_id="user_123", date="2026-08-02")
        assert len(records_aug2) == 0

    await engine.dispose()


# =====================================================================
# 2. MCP SERVER TOOLS TESTS
# =====================================================================

@pytest.mark.anyio
async def test_mcp_tools():
    # Setup test DB
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    # Patch AsyncSessionLocal inside server.py to use our test session factory
    with patch("schedule_mcp_server.server.AsyncSessionLocal", async_session):
        # A. Call add_schedule tool handler
        res = await add_schedule(
            user_id="mcp_user",
            description="Standup meeting",
            time="09:30",
            date="2026-08-10"
        )
        assert res["id"] is not None
        assert res["user_id"] == "mcp_user"
        assert res["description"] == "Standup meeting"
        assert res["date"] == "2026-08-10"
        assert res["time"] == "09:30"

        # B. Call list_schedules tool handler (returns pre-serialized JSON string)
        list_res = await list_schedules(user_id="mcp_user")
        assert isinstance(list_res, str)
        parsed = json.loads(list_res)
        assert len(parsed) == 1
        assert parsed[0]["description"] == "Standup meeting"

        # C. Call list_schedules filtered by date
        list_empty = await list_schedules(user_id="mcp_user", date="2026-08-11")
        assert json.loads(list_empty) == []

        # D. Test validation error handling in server.py
        with pytest.raises(ValueError) as exc:
            await add_schedule(
                user_id="mcp_user",
                description="Failed schedule",
                time="25:99",
                date="2026-08-10"
            )
        assert "time must be in 24-hour HH:MM format" in str(exc.value)

    await engine.dispose()


# =====================================================================
# 3. SCHEDULE SERVICE & MCP CLIENT INTEGRATION TESTS
# =====================================================================

def test_external_mcp_client_normalize():
    # Test _normalize parses JSON strings to Python data structures
    res_dict = ExternalMCPClient._normalize('{"status": "ok", "value": 42}')
    assert res_dict == {"status": "ok", "value": 42}

    res_list = ExternalMCPClient._normalize('[{"id": "1"}, {"id": "2"}]')
    assert res_list == [{"id": "1"}, {"id": "2"}]

    res_invalid_json = ExternalMCPClient._normalize("not-json-string")
    assert res_invalid_json == "not-json-string"

    # Test nested lists of strings
    res_nested = ExternalMCPClient._normalize(['{"a": 1}', "plain-text"])
    assert res_nested == {"a": 1}


@pytest.mark.anyio
async def test_schedule_service():
    mock_mcp_client = AsyncMock()
    service = ScheduleService(mock_mcp_client)

    # A. Test add_schedule calls tool correctly and forwards result
    mock_mcp_client.acall_tool.return_value = {
        "id": "rec_1", "user_id": "u1", "date": "2026-08-01", "time": "10:00", "description": "Review"
    }
    result = await service.add_schedule(
        user_id="u1", description="Review", time="10:00", date="2026-08-01"
    )
    mock_mcp_client.acall_tool.assert_called_once_with(
        "add_schedule",
        {"user_id": "u1", "description": "Review", "time": "10:00", "date": "2026-08-01"}
    )
    assert result["id"] == "rec_1"

    # B. Test date defaulting behavior (omitted from arguments if None)
    mock_mcp_client.reset_mock()
    await service.add_schedule(user_id="u1", description="Review", time="10:00", date=None)
    mock_mcp_client.acall_tool.assert_called_once_with(
        "add_schedule",
        {"user_id": "u1", "description": "Review", "time": "10:00"}
    )

    # C. Test list_schedules tool call
    mock_mcp_client.reset_mock()
    mock_mcp_client.acall_tool.return_value = [
        {"id": "rec_1", "user_id": "u1", "date": "2026-08-01", "time": "10:00", "description": "Review"}
    ]
    schedules = await service.list_schedules(user_id="u1", date="2026-08-01")
    mock_mcp_client.acall_tool.assert_called_once_with(
        "list_schedules",
        {"user_id": "u1", "date": "2026-08-01"}
    )
    assert len(schedules) == 1
    assert schedules[0]["description"] == "Review"

    # D. Test exception wrapping (WebSearchError -> ScheduleError)
    mock_mcp_client.acall_tool.side_effect = WebSearchError("failed connection")
    with pytest.raises(ScheduleError) as exc:
        await service.add_schedule(user_id="u1", description="Review", time="10:00")
    assert "Schedule operation failed: Web search failed: failed connection" in str(exc.value)

    # E. Test generic exception wrapping
    mock_mcp_client.acall_tool.side_effect = Exception("db deadlock")
    with pytest.raises(ScheduleError) as exc:
        await service.list_schedules(user_id="u1")
    assert "db deadlock" in str(exc.value)


# =====================================================================
# 4. LANGGRAPH NODES TESTS
# =====================================================================

@pytest.mark.anyio
async def test_schedule_graph_nodes():
    # A. Test classify_schedule node
    mock_llm = MagicMock()
    mock_llm.classify_schedule_action.return_value = {
        "action": "add",
        "description": "dentist",
        "date": "2026-08-01",
        "time": "14:00",
    }
    classify_node = make_schedule_classification_node(mock_llm)
    state = {"query": "schedule dentist at 2pm on August 1st"}
    updates = classify_node(state)
    assert updates["schedule_action"] == "add"
    assert updates["schedule_description"] == "dentist"
    assert updates["schedule_date"] == "2026-08-01"
    assert updates["schedule_time"] == "14:00"

    # B. Test schedule_add node (Success)
    mock_service = AsyncMock()
    mock_service.add_schedule.return_value = {
        "id": "1", "user_id": "u1", "date": "2026-08-01", "time": "14:00", "description": "dentist"
    }
    add_node = make_schedule_add_node(mock_service)
    state = {
        "user_id": "u1",
        "schedule_description": "dentist",
        "schedule_time": "14:00",
        "schedule_date": "2026-08-01",
    }
    res = await add_node(state)
    assert res["sources"] == []
    assert 'added "dentist" on 2026-08-01 at 14:00' in res["answer"]

    # C. Test schedule_add node (Missing description/time)
    state_missing = {
        "user_id": "u1",
        "schedule_description": "",
        "schedule_time": None
    }
    res_missing = await add_node(state_missing)
    assert "I couldn't tell what to schedule or what time" in res_missing["answer"]

    # D. Test schedule_list node (Success with schedules)
    mock_service.list_schedules.return_value = [
        {"date": "2026-08-01", "time": "14:00", "description": "dentist"},
        {"date": "2026-08-01", "time": "18:00", "description": "dinner"}
    ]
    list_node = make_schedule_list_node(mock_service)
    state_list = {
        "user_id": "u1",
        "schedule_date": "2026-08-01"
    }
    res_list = await list_node(state_list)
    assert "Here's what you have scheduled:" in res_list["answer"]
    assert "- 2026-08-01 at 14:00: dentist" in res_list["answer"]
    assert "- 2026-08-01 at 18:00: dinner" in res_list["answer"]

    # E. Test schedule_list node (No schedules)
    mock_service.list_schedules.return_value = []
    res_empty = await list_node(state_list)
    assert "You don't have any schedules for 2026-08-01" in res_empty["answer"]


# =====================================================================
# 5. CONTROLLER ORCHESTRATION TESTS
# =====================================================================

@pytest.mark.anyio
async def test_chat_controller_schedule_routing():
    mock_retrieval = MagicMock()
    mock_llm = MagicMock()
    mock_web_search = MagicMock()
    mock_schedule = AsyncMock()

    # Instantiate controller
    controller = ChatController(
        retrieval_service=mock_retrieval,
        llm_service=mock_llm,
        web_search_service=mock_web_search,
        schedule_service=mock_schedule
    )

    # Setup mocks for intent classification and listing (using lowercase "list")
    mock_llm.classify_intent.return_value = "schedule"
    mock_llm.classify_schedule_action.return_value = {
        "action": "list",
        "description": None,
        "date": "2026-08-01",
        "time": None
    }
    mock_schedule.list_schedules.return_value = [
        {"date": "2026-08-01", "time": "12:00", "description": "lunch"}
    ]

    events = []
    async for event in controller.astream_answer(
        query="what is my schedule on August 1st?",
        user_id="u1"
    ):
        events.append(event)

    # Verify nodes execution flow
    status_steps = [
        e["data"]["step"] for e in events if e["event"] == "status" and e["data"]["phase"] == "start"
    ]
    assert "detect_intent" in status_steps
    assert "classify_schedule" in status_steps
    assert "schedule_list" in status_steps

    # Verify final result
    done_event = next(e for e in events if e["event"] == "done")
    assert "- 2026-08-01 at 12:00: lunch" in done_event["data"]["answer"]


@pytest.mark.anyio
async def test_chat_session_controller_schedule_integration():
    mock_chat_controller = MagicMock()
    mock_history_service = AsyncMock()

    session_controller = ChatSessionController(
        chat_controller=mock_chat_controller,
        chat_history_service=mock_history_service
    )

    # Setup session database responses
    mock_session = MagicMock()
    mock_session.id = "sess_999"
    mock_session.title = "Schedule Chat"
    mock_history_service.get_session.return_value = mock_session
    mock_history_service.get_recent_messages.return_value = []

    # Mock ChatController event stream
    async def mock_astream(*args, **kwargs):
        yield {"event": "status", "data": {"step": "classify_schedule", "phase": "end", "detail": {"is_followup": False}}}
        yield {"event": "done", "data": {"answer": "Added dentist appointment.", "sources": []}}

    mock_chat_controller.astream_answer.side_effect = mock_astream

    events = []
    async for event in session_controller.stream_chat(
        user_id="u1",
        query="add dentist appointment tomorrow at 10am",
        session_id="sess_999"
    ):
        events.append(event)

    # Verify event stream
    assert len(events) == 3  # session, status, done
    assert events[0]["event"] == "session"
    assert events[1]["event"] == "status"
    assert events[2]["event"] == "done"

    # Verify persistence methods are called
    mock_history_service.append_user_message.assert_called_once_with("sess_999", "add dentist appointment tomorrow at 10am")
    mock_history_service.append_assistant_message.assert_called_once_with(
        "sess_999",
        content="Added dentist appointment.",
        sources=[],
        thought_steps=[{"step": "classify_schedule", "phase": "end", "detail": {"is_followup": False}}],
        is_followup=None,
        rewritten_query=None,
        latency_ms=pytest.approx(0, abs=1000)
    )
