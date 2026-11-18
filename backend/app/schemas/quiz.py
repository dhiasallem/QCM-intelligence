from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class QuizCreate(BaseModel):
    specialty: str = Field(min_length=2, max_length=150)
    subject: str = Field(min_length=2, max_length=150)
    level: str = Field(min_length=2, max_length=80)
    nb_questions: int = Field(ge=1, le=50)
    chapters: str | None = Field(default=None, max_length=1000)


class OptionRead(BaseModel):
    id: int
    text: str
    is_correct: bool

    model_config = {"from_attributes": True}


class QuestionRead(BaseModel):
    id: int
    statement: str
    difficulty: str
    chapter: str | None
    explanation: str | None
    status: str
    options: list[OptionRead]

    model_config = {"from_attributes": True}


class QuizRead(BaseModel):
    id: int
    specialty: str
    subject: str
    level: str
    nb_questions: int
    chapters: str | None
    provider: str | None
    status: str
    error: str | None
    created_at: datetime
    questions: list[QuestionRead] = []

    model_config = {"from_attributes": True}


class QuizSummary(BaseModel):
    id: int
    specialty: str
    subject: str
    level: str
    nb_questions: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OptionIn(BaseModel):
    text: str = Field(min_length=1)
    is_correct: bool


class QuestionUpdate(BaseModel):
    statement: str | None = Field(default=None, min_length=10)
    difficulty: Literal["facile", "moyen", "difficile"] | None = None
    chapter: str | None = None
    explanation: str | None = None
    status: Literal["GENERATED", "VALIDATED", "REJECTED"] | None = None
    options: list[OptionIn] | None = None

    @model_validator(mode="after")
    def check_options(self):
        if self.options is not None:
            if len(self.options) < 3:
                raise ValueError("Il faut au moins 3 propositions")
            if not any(o.is_correct for o in self.options):
                raise ValueError("Il faut au moins une bonne réponse")
        return self