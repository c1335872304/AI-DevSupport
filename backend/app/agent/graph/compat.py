from __future__ import annotations

import inspect
from collections import defaultdict
from typing import Any, Callable

START = "__start__"
END = "__end__"


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


class _CompiledCompatGraph:
    """Tiny development/test fallback for environments without the langgraph package.

    Production installs the real ``langgraph`` dependency. This fallback only implements
    the subset API Assistant uses so isolated unit tests can still exercise the exact workflow
    nodes and routes when third-party packages are unavailable in the execution sandbox.
    """

    def __init__(self, nodes: dict[str, Callable], edges: dict[str, list[str]], conditional: dict[str, tuple[Callable, dict[str, str]]]):
        self.nodes = nodes
        self.edges = edges
        self.conditional = conditional

    async def ainvoke(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        state = dict(initial_state)
        starts = self.edges.get(START, [])
        if len(starts) != 1:
            raise RuntimeError("Compat StateGraph expects exactly one START edge")
        current = starts[0]
        guard = 0
        while current != END:
            guard += 1
            if guard > 256:
                raise RuntimeError("Compat StateGraph exceeded 256 node transitions")
            node = self.nodes.get(current)
            if node is None:
                raise RuntimeError(f"Unknown graph node: {current}")
            update = await _maybe_await(node(state))
            if update:
                state.update(update)
            if current in self.conditional:
                route, mapping = self.conditional[current]
                key = await _maybe_await(route(state))
                current = mapping.get(key, key)
                continue
            next_nodes = self.edges.get(current, [])
            if len(next_nodes) != 1:
                raise RuntimeError(f"Compat StateGraph node {current!r} must have exactly one outgoing edge")
            current = next_nodes[0]
        return state


class StateGraph:
    def __init__(self, state_schema):
        self.state_schema = state_schema
        self.nodes: dict[str, Callable] = {}
        self.edges: dict[str, list[str]] = defaultdict(list)
        self.conditional: dict[str, tuple[Callable, dict[str, str]]] = {}

    def add_node(self, name: str, fn: Callable) -> None:
        self.nodes[name] = fn

    def add_edge(self, source: str, target: str) -> None:
        self.edges[source].append(target)

    def add_conditional_edges(self, source: str, route: Callable, mapping: dict[str, str]) -> None:
        self.conditional[source] = (route, dict(mapping))

    def compile(self):
        return _CompiledCompatGraph(dict(self.nodes), dict(self.edges), dict(self.conditional))
