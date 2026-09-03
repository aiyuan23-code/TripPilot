"""Input models for trip planning requests."""

from datetime import date as Date
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TripPlanRequest(BaseModel):
    """Validated user input required to generate a trip plan."""

    model_config = ConfigDict(extra="forbid")

    city: str = Field(..., min_length=1, description="目的地城市")
    start_date: Date = Field(..., description="旅行开始日期")
    end_date: Date = Field(..., description="旅行结束日期")
    preferences: list[str] = Field(default_factory=list, description="旅行兴趣偏好")
    budget_level: str = Field(
        default="medium",
        min_length=1,
        description="预算级别",
    )
    transportation: str = Field(
        default="public_transport",
        min_length=1,
        description="交通偏好",
    )
    accommodation: str = Field(
        default="economy",
        min_length=1,
        description="住宿类型",
    )

    @field_validator("city", "budget_level", "transportation", "accommodation")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """Normalize required text fields and reject whitespace-only values."""
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("preferences", mode="before")
    @classmethod
    def parse_preferences(cls, value: object) -> object:
        """Accept both the new list format and the chapter's text form."""
        if value is None:
            return []
        if isinstance(value, str):
            return re.split(r"[,，、]", value)
        return value

    @field_validator("preferences")
    @classmethod
    def normalize_preferences(cls, values: list[str]) -> list[str]:
        """Remove blank and duplicate preferences while preserving order."""
        normalized: list[str] = []
        for value in values:
            value = value.strip()
            if value and value not in normalized:
                normalized.append(value)
        return normalized

    @model_validator(mode="after")
    def validate_dates(self) -> "TripPlanRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self

    @property
    def days(self) -> int:
        """Return the inclusive number of calendar days in the trip."""
        return (self.end_date - self.start_date).days + 1
