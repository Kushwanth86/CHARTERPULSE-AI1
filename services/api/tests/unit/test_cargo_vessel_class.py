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
