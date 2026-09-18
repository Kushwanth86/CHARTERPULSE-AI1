import pytest
from pydantic import ValidationError

from services.api.app.schemas.cargo import CargoRequirementCreate


def test_cargo_requires_positive_quantity():
    with pytest.raises(ValidationError):
        CargoRequirementCreate(
            material="Coking Coal",
            quantity_mt=0,
        )


def test_cargo_requires_material():
    with pytest.raises(ValidationError):
        CargoRequirementCreate(
            material="",
            quantity_mt=70000,
        )


def test_cargo_accepts_valid_requirement():
    payload = CargoRequirementCreate(
        cargo_type="DRY_BULK",
        material="Coking Coal",
        quantity_mt=70000,
    )

    assert payload.material == "Coking Coal"
    assert payload.quantity_mt == 70000
    assert payload.cargo_type == "DRY_BULK"


def test_cargo_rejects_latest_delivery_before_earliest_delivery():
    earliest = "2026-10-20T00:00:00+00:00"
    latest = "2026-10-01T00:00:00+00:00"

    with pytest.raises(ValidationError):
        CargoRequirementCreate(
            material="Coking Coal",
            quantity_mt=70000,
            earliest_delivery=earliest,
            latest_delivery=latest,
        )


def test_cargo_rejects_blank_material():
    with pytest.raises(ValidationError):
        CargoRequirementCreate(
            material="   ",
            quantity_mt=70000,
        )
