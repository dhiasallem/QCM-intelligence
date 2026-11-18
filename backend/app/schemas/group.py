from pydantic import BaseModel, Field
from app.schemas.auth import UserOut


class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class GroupSummary(BaseModel):
    id: int
    name: str
    code: str
    teacher_id: int
    student_count: int = 0

    model_config = {"from_attributes": True}


class GroupRead(BaseModel):
    id: int
    name: str
    code: str
    teacher_id: int
    students: list[UserOut] = []

    model_config = {"from_attributes": True}


class AddStudentsRequest(BaseModel):
    student_ids: list[int] = Field(min_length=1)


class JoinGroupRequest(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class StudentGroupItem(BaseModel):
    """Vue d'un groupe côté étudiant (sans la liste des autres membres)."""
    id: int
    name: str
    teacher_name: str
    student_count: int


class JoinGroupResponse(BaseModel):
    group: StudentGroupItem
    new_exams: int  # examens déjà ouverts reçus en rejoignant le groupe
