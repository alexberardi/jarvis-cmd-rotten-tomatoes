"""Pre-route tests for the rotten_tomatoes command."""

import importlib.util
import os

import pytest


def _load_command():
    here = os.path.dirname(os.path.abspath(__file__))
    cmd_path = os.path.join(here, "..", "commands", "rotten_tomatoes", "command.py")
    spec = importlib.util.spec_from_file_location("rt_cmd_under_test", cmd_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.RottenTomatoesCommand


@pytest.fixture
def cmd():
    return _load_command()()


class TestPreRouteInTheaters:
    @pytest.mark.parametrize("phrase", [
        "what's in theaters",
        "what's in theaters right now",
        "what is in theaters now",
        "what's new in theaters",
        "what movies are in theaters",
        "what movies are out right now",
        "what's out in theaters",
        "what's playing in theaters",
        "what's playing at the theater",
        "what's playing right now",
        "in theaters now",
        "in theaters",
        "movies in theaters",
        "new in theaters",
    ])
    def test_in_theaters(self, cmd, phrase):
        result = cmd.pre_route(phrase)
        assert result is not None
        assert result.arguments == {"action": "in_theaters"}


class TestPreRouteNoMatch:
    """Search queries with a movie title need LLM extraction — must fall through."""

    @pytest.mark.parametrize("phrase", [
        "what's the rating for The Shawshank Redemption",
        "is Dune any good",
        "how did Oppenheimer do on rotten tomatoes",
        "tell me a joke",
        "what time is it",
        "",
    ])
    def test_returns_none(self, cmd, phrase):
        assert cmd.pre_route(phrase) is None


class TestFastPathPatterns:
    def test_ids_stable(self, cmd):
        ids = {p.id for p in cmd.fast_path_patterns}
        assert ids == {"rotten_tomatoes.in_theaters"}
