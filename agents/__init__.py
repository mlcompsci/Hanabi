"""Agent registry for the Hanabi reproduction."""

from .base_agent import BaseAgent
from .full_agent import FullAgent
from .intentional_agent import IntentionalAgent
from .outer_agent import OuterAgent

AGENT_TYPES = {
    "outer": OuterAgent,
    "intentional": IntentionalAgent,
    "full": FullAgent,
}


def create_agent(name: str) -> BaseAgent:
    try:
        return AGENT_TYPES[name.lower()]()
    except KeyError as exc:
        raise ValueError(f"Unknown agent type: {name}") from exc

