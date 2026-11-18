from datetime import datetime
from pydantic import BaseModel, Field


# ==========================================
# VUE ÉTUDIANT (PENDANT L'EXAMEN - SÉCURISÉE)
# ==========================================

class StudentOption(BaseModel):
    id: int
    text: str

    model_config = {"from_attributes": True}


class StudentQuestion(BaseModel):
    id: int
    position: int
    statement: str
    difficulty: str
    chapter: str | None = None
    is_multiple_choice: bool = False
    options: list[StudentOption]

    model_config = {"from_attributes": True}


class StudentAttemptTake(BaseModel):
    attempt_id: int
    session_id: int
    quiz_subject: str
    status: str
    started_at: datetime | None
    deadline_at: datetime | None
    remaining_seconds: int
    questions: list[StudentQuestion]
    saved_answers: dict[int, list[int]] = {}  # question_id -> list of selected option ids


class SaveAnswersRequest(BaseModel):
    answers: dict[int, list[int]]  # question_id -> list of selected option ids


class SubmitResponse(BaseModel):
    attempt_id: int
    status: str
    submitted_at: datetime
    message: str


# ==========================================
# VUES RÉSULTATS & CORRECTION (PROF / APRÈS CLÔTURE)
# ==========================================

class ReviewOption(BaseModel):
    id: int
    text: str
    is_correct: bool
    was_selected: bool


class ReviewQuestion(BaseModel):
    question_id: int
    position: int
    statement: str
    difficulty: str
    chapter: str | None = None
    explanation: str | None = None
    options: list[ReviewOption]
    score_earned: float
    max_score: float


class AttemptReview(BaseModel):
    attempt_id: int
    session_id: int
    student_id: int
    student_name: str
    student_email: str
    status: str
    started_at: datetime | None
    submitted_at: datetime | None
    auto_score: float | None
    final_score: float | None
    teacher_comment: str | None
    total_max_score: float
    questions: list[ReviewQuestion]


class AttemptGradeUpdate(BaseModel):
    final_score: float = Field(ge=0.0)
    teacher_comment: str | None = None


class TeacherAttemptItem(BaseModel):
    id: int
    student_id: int
    student_name: str
    student_email: str
    status: str
    started_at: datetime | None
    submitted_at: datetime | None
    auto_score: float | None
    final_score: float | None
    teacher_comment: str | None

    model_config = {"from_attributes": True}


class StudentSessionSummary(BaseModel):
    session_id: int
    attempt_id: int
    quiz_subject: str
    group_name: str | None = None
    opens_at: datetime
    closes_at: datetime
    duration_minutes: int
    status: str  # NOT_STARTED | IN_PROGRESS | SUBMITTED | GRADED
    final_score: float | None = None
    auto_score: float | None = None
    max_score: float | None = None
    can_start: bool = False
