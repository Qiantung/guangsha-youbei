from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    dataset_id: str = "demo_01"
    mode: Literal["simulation", "reference"] = "simulation"
    structure_type: Literal["brick", "frame", "shear_wall"] = "frame"
    fortification_intensity: int = Field(default=7, ge=6, le=9, strict=True)
    pga: float = Field(default=0.25, ge=0, le=3, strict=True)
    building_area: float = Field(default=100, gt=0, le=100000, strict=True)
    floor_count: int = Field(default=6, ge=1, le=100, strict=True)
    age: float = Field(default=45, ge=0, le=120, strict=True)
    sleeping: bool = Field(default=False, strict=True)
    reference_floor_grade: int = Field(default=4, ge=1, le=5, strict=True)


class RunRequest(BaseModel):
    scenario: Scenario = Field(default_factory=Scenario)
    grant: bool = False


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    scenario: Scenario = Field(default_factory=Scenario)
    session_id: str = Field(default="local-demo", min_length=1, max_length=100)
    transport: Literal["core", "mcp"] = "core"


class Redemption(BaseModel):
    dataset_id: str
    item_id: str
    redemption_id: str = Field(min_length=1, max_length=100)


class Reversal(BaseModel):
    dataset_id: str
    redemption_id: str = Field(min_length=1, max_length=100)
