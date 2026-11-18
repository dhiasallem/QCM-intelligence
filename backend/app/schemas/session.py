from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class SessionCreate(BaseModel):
    quiz_id: int
    group_id: int
    opens_at: datetime
    closes_at: datetime
    duration_minutes: int = Field(ge=1, le=360)
    questions_per_student: int = Field(ge=1, le=100)
    points_per_question: float = Field(default=1.0, gt=0)
    scoring_rule: Literal["ALL_OR_NOTHING", "PARTIAL", "PARTIAL_PENALTY"] = "ALL_OR_NOTHING"
    penalty: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.closes_at <= self.opens_at:
            raise ValueError("La date de clôture doit être postérieure à la date d'ouverture")
        return self


class SessionRead(BaseModel):
    id: int
    quiz_id: int
    group_id: int
    opens_at: datetime
    closes_at: datetime
    duration_minutes: int
    questions_per_student: int
    points_per_question: float
    scoring_rule: str
    penalty: float
    status: str

    quiz_subject: str | None = None
    group_name: str | None = None
    total_attempts: int = 0
    submitted_attempts: int = 0

    model_config = {"from_attributes": True}


class SessionSummary(BaseModel):
    id: int
    quiz_id: int
    quiz_subject: str | None = None
    group_id: int
    group_name: str | None = None
    opens_at: datetime
    closes_at: datetime
    duration_minutes: int
    questions_per_student: int
    status: str
    total_attempts: int = 0
    submitted_attempts: int = 0

    model_config = {"from_attributes": True}
