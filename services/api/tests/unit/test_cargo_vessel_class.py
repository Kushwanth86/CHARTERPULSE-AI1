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


@pytest.mark.parametrize("quantity", [True, False])
def test_cargo_requirement_rejects_boolean_quantities(quantity):
    with pytest.raises(ValidationError, match="not a boolean"):
        CargoRequirementCreate(material="Iron Ore", quantity_mt=quantity)


@pytest.mark.parametrize("quantity", [0, -1, -0.000001, "0", "-2"])
def test_cargo_requirement_rejects_non_positive_quantities(quantity):
    with pytest.raises(ValidationError):
        CargoRequirementCreate(material="Iron Ore", quantity_mt=quantity)


@pytest.mark.parametrize("quantity", [0.0000001, 0.125, 1, 70000, 1e12])
def test_cargo_requirement_accepts_positive_finite_quantity_boundaries(quantity):
    payload = CargoRequirementCreate(material="Iron Ore", quantity_mt=quantity)
    assert payload.quantity_mt == quantity


@pytest.mark.parametrize("material", ["", " ", "   ", "\\t\\n"])
def test_cargo_requirement_rejects_empty_material_after_trimming(material):
    with pytest.raises(ValidationError):
        CargoRequirementCreate(material=material, quantity_mt=1)


def test_cargo_requirement_trims_material_and_accepts_fractional_quantity():
    payload = CargoRequirementCreate(material="  Zinc Concentrate  ", quantity_mt=0.125)
    assert payload.material == "Zinc Concentrate"
    assert payload.quantity_mt == 0.125


def test_cargo_requirement_accepts_equal_delivery_dates():
    payload = CargoRequirementCreate(
        material="Iron Ore",
        quantity_mt=1,
        earliest_delivery="2026-10-25T00:00:00+00:00",
        latest_delivery="2026-10-25T00:00:00+00:00",
    )
    assert payload.earliest_delivery == payload.latest_delivery


def test_cargo_requirement_compares_aware_dates_by_instant():
    payload = CargoRequirementCreate(
        material="Iron Ore",
        quantity_mt=1,
        earliest_delivery="2026-10-25T12:00:00+12:00",
        latest_delivery="2026-10-25T01:00:00+00:00",
    )
    assert payload.latest_delivery > payload.earliest_delivery


@pytest.mark.parametrize(
    ("earliest", "latest"),
    [
        ("not-a-date", "2026-10-26T00:00:00"),
        ("2026-10-27T00:00:00", "2026-10-26T00:00:00"),
        ("2026-10-25T00:00:00-05:00", "2026-10-25T00:00:00+00:00"),
    ],
)
def test_cargo_requirement_rejects_malformed_or_reversed_delivery_windows(earliest, latest):
    with pytest.raises(ValidationError):
        CargoRequirementCreate(
            material="Iron Ore",
            quantity_mt=1,
            earliest_delivery=earliest,
            latest_delivery=latest,
        )


def test_cargo_requirement_allows_distinct_route_with_one_endpoint_unspecified():
    origin_id = "00000000-0000-4000-8000-000000000001"
    payload = CargoRequirementCreate(
        material="Iron Ore",
        quantity_mt=1,
        origin_location_id=origin_id,
        destination_location_id=None,
    )
    assert str(payload.origin_location_id) == origin_id
    assert payload.destination_location_id is None


@pytest.mark.parametrize("location_id", ["", "not-a-uuid", "123", "00000000-0000-0000-0000-000000000001"])
def test_cargo_requirement_rejects_malformed_location_ids(location_id):
    with pytest.raises(ValidationError):
        CargoRequirementCreate(
            material="Iron Ore",
            quantity_mt=1,
            origin_location_id=location_id,
        )
