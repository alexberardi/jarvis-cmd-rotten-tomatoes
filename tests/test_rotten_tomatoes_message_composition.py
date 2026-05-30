"""Verify RottenTomatoesCommand.run() composes a `message` on the in_theaters pre-route."""

import importlib.util
import os

import pytest


def _load_command():
    here = os.path.dirname(os.path.abspath(__file__))
    cmd_path = os.path.join(here, "..", "commands", "rotten_tomatoes", "command.py")
    spec = importlib.util.spec_from_file_location("rt_msg_test", cmd_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def cmd_module():
    return _load_command()


def _make_req(is_pre_routed: bool):
    from core.request_information import RequestInformation
    return RequestInformation(
        voice_command="what's in theaters",
        conversation_id="c",
        is_validation_response=False,
        is_pre_routed=is_pre_routed,
    )


def test_in_theaters_message_composed_when_pre_routed(cmd_module, monkeypatch):
    cmd = cmd_module.RottenTomatoesCommand()
    monkeypatch.setattr(
        cmd_module, "browse_in_theaters",
        lambda: [
            {"title": "Movie A", "tomatometer": 90},
            {"title": "Movie B", "tomatometer": 75},
            {"title": "Movie C", "tomatometer": 60},
        ],
    )
    resp = cmd.run(_make_req(is_pre_routed=True), action="in_theaters")
    msg = resp.context_data.get("message")
    assert msg
    assert "Movie A" in msg


def test_in_theaters_no_message_when_not_pre_routed(cmd_module, monkeypatch):
    cmd = cmd_module.RottenTomatoesCommand()
    monkeypatch.setattr(
        cmd_module, "browse_in_theaters",
        lambda: [{"title": "Movie A", "tomatometer": 90}],
    )
    resp = cmd.run(_make_req(is_pre_routed=False), action="in_theaters")
    assert resp.context_data.get("message") is None


def test_in_theaters_empty_message(cmd_module, monkeypatch):
    cmd = cmd_module.RottenTomatoesCommand()
    monkeypatch.setattr(cmd_module, "browse_in_theaters", lambda: [])
    resp = cmd.run(_make_req(is_pre_routed=True), action="in_theaters")
    msg = resp.context_data.get("message")
    assert msg
    assert "couldn't find" in msg.lower() or "no" in msg.lower()
