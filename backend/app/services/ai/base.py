from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class OptionOut(BaseModel):
    texte: str = Field(min_length=1)
    correcte: bool


class QuestionOut(BaseModel):
    enonce: str = Field(min_length=10)
    difficulte: Literal["facile", "moyen", "difficile"]
    chapitre: str = ""
    options: list[OptionOut] = Field(min_length=3, max_length=6)
    explication: str = ""

    @field_validator("difficulte", mode="before")
    @classmethod
    def normaliser_difficulte(cls, v):
        return str(v).strip().lower()

    @model_validator(mode="after")
    def verifier_options(self):
        if not any(o.correcte for o in self.options):
            raise ValueError("aucune bonne réponse")
        textes = [o.texte.strip().lower() for o in self.options]
        if len(set(textes)) != len(textes):
            raise ValueError("options dupliquées")
        return self


class QuizOut(BaseModel):
    questions: list[QuestionOut]


class QuestionGenerator(ABC):
    name: str = ""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Retourne le texte JSON brut produit par l'IA."""