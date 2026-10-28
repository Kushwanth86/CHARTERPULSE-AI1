from __future__ import annotations

from types import SimpleNamespace

from scripts import import_baltic_exchange as importer


class DuplicateKeyError(Exception):
    code = "23505"


class Query:
    def __init__(self, table, state):
        self.table = table
        self.state = state
        self.reference = None
        self.payload = None

    def select(self, _columns):
        return self

    def eq(self, column, value):
        if column == "source_reference":
            self.reference = value
        return self

    def limit(self, _count):
        return self

    def insert(self, payload):
        self.payload = payload
        self.reference = payload["source_reference"]
        return self

    def execute(self):
        if self.payload is None:
            exists = self.reference in self.state["references"]
            return SimpleNamespace(data=[{"id": "existing"}] if exists else [])
        if self.reference in self.state["references"]:
            raise DuplicateKeyError("duplicate Baltic source reference")
        self.state["references"].add(self.reference)
        return SimpleNamespace(data=[{"id": "new"}])


class FakeClient:
    def __init__(self):
        self.state = {"references": set()}

    def table(self, name):
        assert name == "market_observations"
        return Query(name, self.state)


def test_import_counts_existing_references_without_reinserting(monkeypatch):
    client = FakeClient()
    client.state["references"].add("baltic-exchange:C5:2026-10-20")
    monkeypatch.setattr(importer, "get_supabase_admin_client", lambda: client)

    inserted, existing = importer._upsert_observations([
        {"source_reference": "baltic-exchange:C5:2026-10-20"},
        {"source_reference": "baltic-exchange:C5:2026-10-21"},
    ])

    assert (inserted, existing) == (1, 1)
    assert client.state["references"] == {
        "baltic-exchange:C5:2026-10-20",
        "baltic-exchange:C5:2026-10-21",
    }


def test_import_treats_concurrent_unique_conflict_as_existing(monkeypatch):
    client = FakeClient()
    original_table = client.table

    class RacingQuery(Query):
        def execute(self):
            if self.payload is not None and self.reference not in self.state["references"]:
                # Simulate another importer winning after our pre-insert read.
                self.state["references"].add(self.reference)
                raise DuplicateKeyError("duplicate Baltic source reference")
            return super().execute()

    def racing_table(name):
        assert name == "market_observations"
        return RacingQuery(name, client.state)

    monkeypatch.setattr(importer, "get_supabase_admin_client", lambda: client)
    monkeypatch.setattr(client, "table", racing_table)

    inserted, existing = importer._upsert_observations([
        {"source_reference": "baltic-exchange:C5:2026-10-20"},
    ])

    assert (inserted, existing) == (0, 1)
