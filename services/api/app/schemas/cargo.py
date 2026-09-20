from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class CargoRequirementCreate(BaseModel):
    cargo_type: str | None = None
    material: str = Field(min_length=1)
    quantity_mt: float = Field(gt=0)

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

    @model_validator(mode="after")
    def validate_delivery_window(self):
        if (
            self.earliest_delivery is not None
            and self.latest_delivery is not None
            and self.latest_delivery < self.earliest_delivery
        ):
            raise ValueError(
                "latest_delivery must be greater than or equal to earliest_delivery"
            )
        return self


class CargoRequirementResponse(CargoRequirementCreate):
    id: UUID
    status: str

    created_at: datetime
    updated_at: datetime
        