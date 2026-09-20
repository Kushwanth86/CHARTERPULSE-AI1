from datetime import datetime, timedelta, timezone

from services.api.app.intelligence.physical_feasibility import PhysicalFeasibilityEngine


def _cargo(**overrides):
    value = {
        "cargo_type": "DRY_BULK",
        "material": "Coking Coal",
        "quantity_mt": 70000,
        "earliest_delivery": datetime.now(timezone.utc).isoformat(),
        "latest_delivery": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    }
    value.update(overrides)
    return value


def _vessel(**overrides):
    value = {
        "name": "CP TEST BULK 01",
        "ship_type": "BULK_CARRIER",
        "vessel_class": "PANAMAX",
        "cargo_capacity_mt": 80000,
        "dwt_mt": 82000,
        "loa_m": 225.0,
        "beam_m": 32.2,
        "max_draft_m": 13.5,
    }
    value.update(overrides)
    return value


def _constraints(**overrides):
    value = {
        "max_loa_m": 230.0,
        "max_beam_m": 33.0,
        "max_draft_m": 14.0,
        "cargo_handling_types": ["DRY_BULK"],
        "max_vessel_capacity_mt": 85000.0,
        "loading_available": True,
        "discharge_available": True,
    }
    value.update(overrides)
    return value


def _compatibility(**overrides):
    value = {
        "vessel_id": "test-vessel",
        "cargo_type": "DRY_BULK",
        "allowed": True,
    }
    value.update(overrides)
    return [value]


def test_feasible_bulk_vessel_with_explicit_compatibility():
    result = PhysicalFeasibilityEngine().evaluate(
        _cargo(), _vessel(), _constraints(), _constraints(), _compatibility()
    )

    assert result["result"] == "FEASIBLE"
    assert result["cargo_capacity_ok"] is True
    assert result["cargo_compatibility_ok"] is True
    assert result["delivery_window_ok"] is True
    assert result["provenance"] == "DERIVED"


def test_missing_vessel_compatibility_requires_review():
    result = PhysicalFeasibilityEngine().evaluate(
        _cargo(), _vessel(), _constraints(), _constraints(), []
    )

    assert result["result"] == "REVIEW"
    assert result["cargo_compatibility_ok"] is None


def test_explicit_incompatibility_is_infeasible():
    result = PhysicalFeasibilityEngine().evaluate(
        _cargo(), _vessel(), _constraints(), _constraints(), _compatibility(allowed=False)
    )

    assert result["result"] == "INFEASIBLE"
    assert result["cargo_compatibility_ok"] is False


def test_insufficient_capacity_is_infeasible():
    result = PhysicalFeasibilityEngine().evaluate(
        _cargo(quantity_mt=90000), _vessel(), _constraints(), _constraints(), _compatibility()
    )

    assert result["result"] == "INFEASIBLE"
    assert result["cargo_capacity_ok"] is False
    assert any("capacity" in reason.lower() for reason in result["reasons"])


def test_port_dimension_violation_is_infeasible():
    result = PhysicalFeasibilityEngine().evaluate(
        _cargo(), _vessel(loa_m=250.0), _constraints(), _constraints(), _compatibility()
    )

    assert result["result"] == "INFEASIBLE"
    assert result["origin_loa_ok"] is False


def test_missing_port_constraints_requires_review():
    result = PhysicalFeasibilityEngine().evaluate(
        _cargo(), _vessel(), None, _constraints(), _compatibility()
    )

    assert result["result"] == "REVIEW"
    assert result["origin_loa_ok"] is None
    assert result["destination_loa_ok"] is True


def test_missing_port_handling_data_requires_review():
    result = PhysicalFeasibilityEngine().evaluate(
        _cargo(),
        _vessel(),
        _constraints(cargo_handling_types=None),
        _constraints(),
        _compatibility(),
    )

    assert result["result"] == "REVIEW"


def test_expired_delivery_deadline_is_infeasible():
    result = PhysicalFeasibilityEngine().evaluate(
        _cargo(latest_delivery=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat()),
        _vessel(),
        _constraints(),
        _constraints(),
        _compatibility(),
    )

    assert result["result"] == "INFEASIBLE"
    assert result["delivery_window_ok"] is False


def test_missing_required_data_requires_review_not_false_feasibility():
    result = PhysicalFeasibilityEngine().evaluate(
        _cargo(quantity_mt=None), _vessel(), _constraints(), _constraints(), _compatibility()
    )

    assert result["result"] == "REVIEW"
    assert result["cargo_capacity_ok"] is None


def test_feasibility_rejects_vessel_when_dwt_exceeds_port_limit():
    result = PhysicalFeasibilityEngine().evaluate(
        _cargo(quantity_mt=70000),
        _vessel(
            cargo_capacity_mt=80000,
            dwt_mt=90000,
        ),
        _constraints(max_vessel_capacity_mt=85000),
        _constraints(max_vessel_capacity_mt=85000),
        _compatibility(),
    )

    assert result["result"] == "INFEASIBLE"
    assert result["cargo_capacity_ok"] is True
    assert result["checks"]["vessel_dwt_ok"] is False
    assert any(
        "DWT exceeds" in reason
        for reason in result["reasons"]
    )
