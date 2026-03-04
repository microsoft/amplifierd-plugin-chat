import pytest
from chat_plugin.commands import CommandProcessor


@pytest.fixture
def processor():
    return CommandProcessor(session_manager=None, event_bus=None)


def test_process_input_recognizes_command(processor):
    action, data = processor.process_input("/help")
    assert action == "command"
    assert data["command"] == "help"


def test_process_input_recognizes_command_with_args(processor):
    action, data = processor.process_input("/mode debug")
    assert action == "command"
    assert data["command"] == "mode"
    assert data["args"] == ["debug"]


def test_process_input_non_command(processor):
    action, data = processor.process_input("hello world")
    assert action == "prompt"
    assert data["text"] == "hello world"


def test_help_command(processor):
    result = processor.handle_command("help", [], session_id=None)
    assert result["type"] == "help"
    assert len(result["data"]["commands"]) > 0


def test_unknown_command(processor):
    result = processor.handle_command("nonexistent", [], session_id=None)
    assert result["type"] == "error"


def test_command_endpoint(client):
    resp = client.post("/chat/command", json={"command": "/help"})
    assert resp.status_code == 200
    assert resp.json()["type"] == "help"
