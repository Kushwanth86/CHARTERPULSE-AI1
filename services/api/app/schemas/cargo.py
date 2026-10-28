from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


VALID_PRIORITIES = {"LOW", "NORMAL", "HIGH", "CRITICAL"}


class CargoRequirementCreate(BaseModel):
    cargo_type: str | None = None
    vessel_class: str | None = None
    material: str = Field(min_length=1)
    quantity_mt: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("quantity_mt", mode="before")
    @classmethod
    def reject_boolean_quantity(cls, value):
        # Python treats bool as an int subclass; never interpret JSON true/false as MT.
        if isinstance(value, bool):
            raise ValueError("quantity_mt must be a numeric quantity, not a boolean")
        return value

    origin_location_id: UUID | None = None
    destination_location_id: UUID | None = None

    earliest_delivery: datetime | None = None
    latest_delivery: datetime | None = None

    priority: str = "NORMAL"

    provenance: str = "USER_PROVIDED"
    source: str | None = None
    source_reference: str | None = None

    @field_validator("material")
    @classmethod
    def validate_material(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("material must not be blank")
        return value

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in VALID_PRIORITIES:
            raise ValueError(
                "priority must be one of LOW, NORMAL, HIGH, or CRITICAL"
            )
        return value

    @model_validator(mode="after")
    def validate_delivery_window(self):
        if (
            self.earliest_delivery is not None
            and self.latest_delivery is not None
        ):
            earliest_aware = self.earliest_delivery.utcoffset() is not None
            latest_aware = self.latest_delivery.utcoffset() is not None
            if earliest_aware != latest_aware:
                raise ValueError(
                    "earliest_delivery and latest_delivery must both include "
                    "a timezone or both omit it"
                )
            if self.latest_delivery < self.earliest_delivery:
                raise ValueError(
                    "latest_delivery must be greater than or equal to earliest_delivery"
                )

        for field_name in ("origin_location_id", "destination_location_id"):
            location_id = getattr(self, field_name)
            if location_id is not None and location_id.version is None:
                raise ValueError(f"{field_name} must be a versioned UUID")

        if (
            self.origin_location_id is not None
            and self.destination_location_id is not None
            and self.origin_location_id == self.destination_location_id
        ):
            raise ValueError(
                "origin_location_id and destination_location_id must be different"
            )
        return self


class CargoRequirementResponse(CargoRequirementCreate):
    id: UUID
    status: str

    created_at: datetime
    updated_at: datetime
