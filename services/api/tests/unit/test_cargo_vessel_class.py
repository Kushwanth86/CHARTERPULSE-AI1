import pytest
from pydantic import ValidationError

from services.api.app.schemas.cargo import CargoRequirementCreate


def test_cargo_requirement_preserves_selected_vessel_class():
    payload = CargoRequirementCreate(
        cargo_type="DRY_BULK",
        vessel_class="Panamax",
        material="Iron Ore",
        quantity_mt=1234.5,
        priority="HIGH",
    )

    assert payload.vessel_class == "Panamax"
    assert payload.model_dump()["vessel_class"] == "Panamax"


def test_cargo_requirement_allows_unspecified_vessel_class():
    payload = CargoRequirementCreate(
        cargo_type="DRY_BULK",
        material="Limestone",
        quantity_mt=25,
    )

    assert payload.vessel_class is None


@pytest.mark.parametrize("quantity", [float("inf"), float("-inf"), float("nan")])
def test_cargo_requirement_rejects_non_finite_quantities(quantity):
    with pytest.raises(ValidationError):
        CargoRequirementCreate(material="Iron Ore", quantity_mt=quantity)


@pytest.mark.parametrize("priority", ["urgent", "P0", "", "  "])
def test_cargo_requirement_rejects_unknown_priorities(priority):
    with pytest.raises(ValidationError):
        CargoRequirementCreate(
            material="Iron Ore",
            quantity_mt=100,
            priority=priority,
        )


@pytest.mark.parametrize(
    ("priority", "expected"),
    [("low", "LOW"), (" NORMAL ", "NORMAL"), ("High", "HIGH"), ("critical", "CRITICAL")],
)
def test_cargo_requirement_normalizes_supported_priorities(priority, expected):
    payload = CargoRequirementCreate(
        material="Iron Ore",
        quantity_mt=100,
        priority=priority,
    )
    assert payload.priority == expected


def test_cargo_requirement_rejects_same_origin_and_destination():
    location_id = "00000000-0000-4000-8000-000000000001"
    with pytest.raises(ValidationError, match="must be different"):
        CargoRequirementCreate(
            material="Iron Ore",
            quantity_mt=100,
            origin_location_id=location_id,
            destination_location_id=location_id,
        )


def test_cargo_requirement_rejects_mixed_timezone_delivery_dates():
    with pytest.raises(ValidationError, match="must both include a timezone"):
        CargoRequirementCreate(
            material="Iron Ore",
            quantity_mt=100,
            earliest_delivery="2026-10-25T00:00:00",
            latest_delivery="2026-10-26T00:00:00+00:00",
        )
