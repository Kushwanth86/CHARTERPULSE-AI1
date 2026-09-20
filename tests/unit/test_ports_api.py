from services.api.app.api.ports import list_ports


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.like_args = None

    def select(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def like(self, column, pattern):
        self.like_args = (column, pattern)
        return self

    def execute(self):
        return FakeResponse(self.rows)


class FakeClient:
    def __init__(self, rows):
        self.query = FakeQuery(rows)

    def table(self, _name):
        return self.query


def test_ports_route_applies_iso2_prefix_filter(monkeypatch):
    query = FakeQuery(
        [
            {"id": "in-1", "unlocode": "INPRT"},
            {"id": "in-2", "unlocode": "INDMQ"},
        ]
    )
    monkeypatch.setattr(
        "services.api.app.api.ports.get_supabase_client",
        lambda: FakeClient(query.rows),
    )

    result = list_ports(country_code="in", limit=100)

    assert query.like_args is None or query.like_args == ("unlocode", "IN%")
    assert result["count"] == 2
    assert all(row["unlocode"].startswith("IN") for row in result["data"])
