"""WeaviateVectorStore fails fast (and recovers) when the server is unreachable."""

import pytest

from src.search import vector_store as vs
from src.search.vector_store import VectorStoreUnavailable, WeaviateVectorStore


def make_store(monkeypatch, probe):
    store = WeaviateVectorStore(url="http://localhost:8080", grpc_port=50051, collection="T")
    monkeypatch.setattr(store, "_probe", probe)
    return store


def test_probe_failure_raises_unavailable_and_starts_cooldown(monkeypatch):
    calls = []

    def probe():
        calls.append(1)
        raise ConnectionRefusedError("refused")

    store = make_store(monkeypatch, probe)
    with pytest.raises(VectorStoreUnavailable):
        store._call(lambda: "never runs")
    with pytest.raises(VectorStoreUnavailable):
        store._call(lambda: "never runs")
    assert len(calls) == 1  # second call short-circuited by the cooldown


def test_recovers_after_cooldown(monkeypatch):
    state = {"up": False, "now": 1000.0}
    monkeypatch.setattr(vs.time, "monotonic", lambda: state["now"])

    def probe():
        if not state["up"]:
            raise ConnectionRefusedError("refused")

    store = make_store(monkeypatch, probe)
    with pytest.raises(VectorStoreUnavailable):
        store._call(lambda: 1)
    state["up"] = True
    with pytest.raises(VectorStoreUnavailable):  # still cooling down
        store._call(lambda: 1)
    state["now"] += vs.UNAVAILABLE_COOLDOWN_S + 1
    assert store._call(lambda: 42) == 42


def test_connection_error_from_call_marks_down(monkeypatch):
    store = make_store(monkeypatch, lambda: None)

    def boom():
        raise RuntimeError("failed to connect to all addresses")

    with pytest.raises(VectorStoreUnavailable):
        store._call(boom)
    with pytest.raises(VectorStoreUnavailable):
        store._call(lambda: "never runs")


def test_other_errors_propagate_unchanged(monkeypatch):
    store = make_store(monkeypatch, lambda: None)

    def bad():
        raise ValueError("chunk is missing an embedding")

    with pytest.raises(ValueError):
        store._call(bad)
    assert store._call(lambda: "ok") == "ok"  # no cooldown for non-connection errors
