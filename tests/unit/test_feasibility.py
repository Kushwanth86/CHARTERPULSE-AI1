from uuid import uuid4

from services.api.app.intelligence.physical_feasibility import (
    PhysicalFeasibilityEngine,
)
from services.api.app.schemas.feasibility import FeasibilityRequest
from services.api.app.services.feasibility_service import FeasibilityService


def test_feasibility_returns_feasible_when_all_required_checks_pass():
    engine = PhysicalFeasibilityEngine()

    result = engine.evaluate(
        cargo={
            "quantity_mt": 10000,
            "cargo_type": "DRY_BULK",
            "latest_delivery": "2099-01-01T00:00:00+00:00",
        },
        vessel={
            "cargo_capacity_mt": 20000,
            "dwt_mt": 25000,
            "loa_m": 200,
            "beam_m": 30,
            "max_draft_m": 10,
        },
        origin_constraints={
            "max_vessel_capacity_mt": 30000,
            "max_loa_m": 250,
            "max_beam_m": 40,
            "max_draft_m": 14,
            "cargo_handling_types": ["DRY_BULK"],
            "loading_available": True,
            "discharge_available": True,
        },
        destination_constraints={
            "max_vessel_capacity_mt": 30000,
            "max_loa_m": 250,
            "max_beam_m": 40,
            "max_draft_m": 14,
            "cargo_handling_types": ["DRY_BULK"],
            "loading_available": True,
            "discharge_available": True,
        },
        vessel_compatibility=[
            {
                "cargo_type": "DRY_BULK",
                "allowed": True,
            }
        ],
    )

    assert result["result"] == "FEASIBLE"
    assert result["provenance"] == "DERIVED"


def test_feasibility_returns_infeasible_when_vessel_exceeds_port_limit():
    engine = PhysicalFeasibilityEngine()

    result = engine.evaluate(
        cargo={
            "quantity_mt": 10000,
            "cargo_type": "DRY_BULK",
            "latest_delivery": "2099-01-01T00:00:00+00:00",
        },
        vessel={
            "cargo_capacity_mt": 20000,
            "dwt_mt": 25000,
            "loa_m": 300,
            "beam_m": 30,
            "max_draft_m": 10,
        },
        origin_constraints={
            "max_vessel_capacity_mt": 30000,
            "max_loa_m": 250,
            "max_beam_m": 40,
            "max_draft_m": 14,
            "cargo_handling_types": ["DRY_BULK"],
            "loading_available": True,
            "discharge_available": True,
        },
        destination_constraints={
            "max_vessel_capacity_mt": 30000,
            "max_loa_m": 350,
            "max_beam_m": 40,
            "max_draft_m": 14,
            "cargo_handling_types": ["DRY_BULK"],
            "loading_available": True,
            "discharge_available": True,
        },
        vessel_compatibility=[
            {
                "cargo_type": "DRY_BULK",
                "allowed": True,
            }
        ],
    )

    assert result["result"] == "INFEASIBLE"
    assert result["origin_loa_ok"] is False


def test_feasibility_returns_review_when_required_data_is_unknown():
    engine = PhysicalFeasibilityEngine()

    result = engine.evaluate(
        cargo={
            "quantity_mt": 10000,
            "cargo_type": "DRY_BULK",
            "latest_delivery": "2099-01-01T00:00:00+00:00",
        },
        vessel={
            "cargo_capacity_mt": 20000,
            "dwt_mt": 25000,
            "loa_m": 200,
            "beam_m": 30,
            "max_draft_m": 10,
        },
        origin_constraints=None,
        destination_constraints={
            "max_vessel_capacity_mt": 30000,
            "max_loa_m": 250,
            "max_beam_m": 40,
            "max_draft_m": 14,
            "cargo_handling_types": ["DRY_BULK"],
            "loading_available": True,
            "discharge_available": True,
        },
        vessel_compatibility=[
            {
                "cargo_type": "DRY_BULK",
                "allowed": True,
            }
        ],
    )

    assert result["result"] == "REVIEW"
    assert result["provenance"] == "DERIVED"


class FakeRepository:
    def __init__(self, rows=None):
        self.rows = rows or {}
        self.created = None

    def get(self, identifier):
        return self.rows.get(str(identifier))

    def list_for_vessel(self, vessel_id):
        return self.rows.get("compatibility", [])

    def create(self, payload):
        self.created = payload
        return payload | {"id": uuid4()}


def test_feasibility_service_orchestrates_dependencies_and_persists_result():
    cargo_id = uuid4()
    vessel_id = uuid4()
    origin_port_id = uuid4()
    destination_port_id = uuid4()

    cargo = {
        "cargo_type": "DRY_BULK",
        "material": "Coking Coal",
        "quantity_mt": 70000,
        "latest_delivery": "2099-01-01T00:00:00+00:00",
    }

    vessel = {
        "name": "CP TEST BULK 01",
        "cargo_capacity_mt": 80000,
        "dwt_mt": 82000,
        "loa_m": 225.0,
        "beam_m": 32.2,
        "max_draft_m": 13.5,
    }

    constraints = {
        "max_loa_m": 230.0,
        "max_beam_m": 33.0,
        "max_draft_m": 14.0,
        "cargo_handling_types": ["DRY_BULK"],
        "max_vessel_capacity_mt": 85000.0,
        "loading_available": True,
        "discharge_available": True,
    }

    compatibility = [
        {
            "cargo_type": "DRY_BULK",
            "allowed": True,
        }
    ]

    cargo_repository = FakeRepository(
        {
            str(cargo_id): cargo,
        }
    )

    vessel_repository = FakeRepository(
        {
            str(vessel_id): vessel,
        }
    )

    constraint_repository = FakeRepository(
        {
            str(origin_port_id): constraints,
            str(destination_port_id): constraints,
        }
    )

    compatibility_repository = FakeRepository(
        {
            "compatibility": compatibility,
        }
    )

    feasibility_repository = FakeRepository()

    service = FeasibilityService()
    service.cargo_repository = cargo_repository
    service.vessel_repository = vessel_repository
    service.constraint_repository = constraint_repository
    service.compatibility_repository = compatibility_repository
    service.feasibility_repository = feasibility_repository

    payload = FeasibilityRequest(
        cargo_requirement_id=cargo_id,
        vessel_id=vessel_id,
        origin_port_id=origin_port_id,
        destination_port_id=destination_port_id,
    )

    result = service.evaluate(payload)

    assert result["result"] == "FEASIBLE"
    assert result["provenance"] == "DERIVED"

    assert result["cargo_requirement_id"] == str(cargo_id)
    assert result["vessel_id"] == str(vessel_id)
    assert result["origin_port_id"] == str(origin_port_id)
    assert result["destination_port_id"] == str(destination_port_id)

    assert feasibility_repository.created is not None
    assert feasibility_repository.created["result"] == "FEASIBLE"
    assert feasibility_repository.created["cargo_compatibility_ok"] is True
    assert feasibility_repository.created["origin_loa_ok"] is True
    assert feasibility_repository.created["destination_loa_ok"] is True
