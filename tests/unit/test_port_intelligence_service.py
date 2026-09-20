from uuid import uuid4

from services.api.app.services.port_intelligence_service import PortIntelligenceService


class FakeResponse:
    def __init__(self, data):
        self.data = data
        self.count = None


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def range(self, *args, **kwargs):
        return self

    def ilike(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def execute(self):
        return FakeResponse(self.rows)


class FakeClient:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return FakeQuery(self.tables[name])


def test_search_ports_overlays_constraint_dimensions(monkeypatch):
    port_id = str(uuid4())
    location_id = str(uuid4())
    country_id = str(uuid4())

    client = FakeClient(
        {
            "ports": [
                {
                    "id": port_id,
                    "location_id": location_id,
                    "name": "Dhamra Port",
                    "latitude": 20.75,
                    "longitude": 86.95,
                    "max_draft_m": None,
                    "max_loa_m": None,
                    "max_beam_m": None,
                    "annual_capacity_tonnes": None,
                    "storage_capacity_tonnes": None,
                    "rail_connected": True,
                    "road_connected": None,
                    "pipeline_connected": None,
                    "unlocode": "INDMQ",
                    "source": "UNECE UN/LOCODE",
                    "source_url": "https://example.test/unlocode",
                    "observed_at": None,
                    "updated_at": None,
                }
            ],
            "port_constraints": [
                {
                    "port_id": port_id,
                    "max_draft_m": 19.0,
                    "max_loa_m": 350.0,
                    "max_beam_m": 50.0,
                    "loading_available": None,
                    "discharge_available": None,
                    "cargo_handling_types": None,
                    "provenance": "REAL",
                    "source": "NGA World Port Index",
                    "source_reference": "WPI",
                    "observed_at": None,
                    "operational_provenance": {},
                }
            ],
            "locations": [
                {
                    "id": location_id,
                    "country_id": country_id,
                    "region_id": None,
                    "name": "Dhamra",
                    "latitude": 20.75,
                    "longitude": 86.95,
                    "timezone": None,
                }
            ],
            "countries": [
                {
                    "id": country_id,
                    "iso2": "IN",
                    "iso3": "IND",
                    "name": "India",
                }
            ],
        }
    )

    monkeypatch.setattr(
        "services.api.app.services.port_intelligence_service.get_supabase_client",
        lambda: client,
    )

    result = PortIntelligenceService().search_ports(query="Dhamra")

    assert len(result) == 1
    assert result[0]["max_draft_m"] == 19.0
    assert result[0]["max_loa_m"] == 350.0
    assert result[0]["max_beam_m"] == 50.0
    assert result[0]["rail_connected"] is True
