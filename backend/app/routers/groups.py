from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, joinedload

from app.db import get_db
from app.deps import require_role
from app.models.exam import Attempt, ExamSession
from app.models.user import User, Group, generate_group_code
from app.routers.sessions import generate_attempts, load_session_questions
from app.schemas.group import (
    GroupCreate, GroupRead, GroupSummary, AddStudentsRequest,
    JoinGroupRequest, JoinGroupResponse, StudentGroupItem,
)

router = APIRouter(prefix="/groups", tags=["groups"])
teacher_or_admin = require_role("teacher", "admin")
student_only = require_role("student")


def unique_group_code(db: Session) -> str:
    while True:
        code = generate_group_code()
        if not db.scalar(select(Group.id).where(Group.code == code)):
            return code


def normalize_code(code: str) -> str:
    return code.strip().upper().replace(" ", "").replace("-", "")


def get_owned_group(db: Session, group_id: int, user: User) -> Group:
    group = db.scalar(
        select(Group)
        .where(Group.id == group_id)
        .options(selectinload(Group.students))
    )
    if not group or (user.role != "admin" and group.teacher_id != user.id):
        raise HTTPException(status_code=404, detail="Groupe introuvable")
    return group


def to_student_item(group: Group) -> StudentGroupItem:
    return StudentGroupItem(
        id=group.id,
        name=group.name,
        teacher_name=group.teacher.name if group.teacher else "Enseignant",
        student_count=len(group.students),
    )


# ---------- Espace étudiant ----------
# Déclarées avant /{group_id} pour que "mine" et "join" ne soient pas pris pour un id.

@router.get("/mine", response_model=list[StudentGroupItem])
def list_my_groups(db: Session = Depends(get_db), user: User = Depends(student_only)):
    """Groupes dont l'étudiant connecté est membre."""
    groups = db.scalars(
        select(Group)
        .where(Group.students.any(User.id == user.id))
        .options(joinedload(Group.teacher), selectinload(Group.students))
        .order_by(Group.name)
    ).all()
    return [to_student_item(g) for g in groups]


@router.post("/join", response_model=JoinGroupResponse)
def join_group(
    data: JoinGroupRequest,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    """Rejoint un groupe avec son code d'accès et reçoit les examens déjà ouverts du groupe."""
    group = db.scalar(
        select(Group)
        .where(Group.code == normalize_code(data.code))
        .options(joinedload(Group.teacher), selectinload(Group.students))
    )
    if not group:
        raise HTTPException(status_code=404, detail="Aucun groupe ne correspond à ce code")
    if any(s.id == user.id for s in group.students):
        raise HTTPException(status_code=409, detail="Vous faites déjà partie de ce groupe")

    group.students.append(user)

    # Les sessions déjà publiées et pas encore clôturées : générer la copie du nouvel étudiant
    now = datetime.now(timezone.utc)
    new_exams = 0
    open_sessions = db.scalars(
        select(ExamSession).where(ExamSession.group_id == group.id, ExamSession.status == "OPEN")
    ).all()
    for sess in open_sessions:
        closes_at = sess.closes_at if sess.closes_at.tzinfo else sess.closes_at.replace(tzinfo=timezone.utc)
        if closes_at <= now:
            continue
        questions = load_session_questions(db, sess)
        if len(questions) < sess.questions_per_student:
            continue
        new_exams += generate_attempts(db, sess, [user], questions)

    db.commit()
    db.refresh(group)
    return JoinGroupResponse(group=to_student_item(group), new_exams=new_exams)


@router.post("/{group_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_group(
    group_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    """L'étudiant quitte le groupe.

    Ses copies non commencées des sessions de ce groupe sont supprimées ; les copies
    commencées ou rendues sont conservées (notes et historique).
    """
    group = db.scalar(
        select(Group).where(Group.id == group_id).options(selectinload(Group.students))
    )
    member = next((s for s in group.students if s.id == user.id), None) if group else None
    if not member:
        raise HTTPException(status_code=404, detail="Vous ne faites pas partie de ce groupe")

    group.students.remove(member)
    unstarted = db.scalars(
        select(Attempt)
        .join(ExamSession, Attempt.session_id == ExamSession.id)
        .where(
            ExamSession.group_id == group.id,
            Attempt.student_id == user.id,
            Attempt.status == "NOT_STARTED",
        )
    ).all()
    for a in unstarted:
        db.delete(a)
    db.commit()


# ---------- Espace enseignant ----------

@router.post("", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(
    data: GroupCreate,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    group = Group(name=data.name.strip(), teacher_id=user.id, code=unique_group_code(db))
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("", response_model=list[GroupSummary])
def list_groups(
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    query = select(Group).options(selectinload(Group.students)).order_by(Group.id.desc())
    if user.role != "admin":
        query = query.where(Group.teacher_id == user.id)
    groups = db.scalars(query).all()

    return [
        GroupSummary(
            id=g.id,
            name=g.name,
            code=g.code,
            teacher_id=g.teacher_id,
            student_count=len(g.students),
        )
        for g in groups
    ]


@router.get("/{group_id}", response_model=GroupRead)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    return get_owned_group(db, group_id, user)


@router.post("/{group_id}/regenerate-code", response_model=GroupRead)
def regenerate_group_code(
    group_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    """Remplace le code d'accès (l'ancien ne fonctionne plus ; les membres actuels restent)."""
    group = get_owned_group(db, group_id, user)
    group.code = unique_group_code(db)
    db.commit()
    db.refresh(group)
    return group


@router.post("/{group_id}/students", response_model=GroupRead)
def add_students_to_group(
    group_id: int,
    data: AddStudentsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    group = get_owned_group(db, group_id, user)
    existing_ids = {s.id for s in group.students}

    students = db.scalars(
        select(User).where(User.id.in_(data.student_ids), User.role == "student")
    ).all()

    for s in students:
        if s.id not in existing_ids:
            group.students.append(s)

    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}/students/{student_id}", response_model=GroupRead)
def remove_student_from_group(
    group_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    group = get_owned_group(db, group_id, user)
    student = next((s for s in group.students if s.id == student_id), None)
    if not student:
        raise HTTPException(status_code=404, detail="Étudiant non trouvé dans ce groupe")

    group.students.remove(student)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    group = get_owned_group(db, group_id, user)
    nb_sessions = db.query(ExamSession).filter(ExamSession.group_id == group.id).count()
    if nb_sessions:
        raise HTTPException(
            status_code=409,
            detail=f"Ce groupe a {nb_sessions} session(s) d'examen : supprimez-les d'abord",
        )
    db.delete(group)
    db.commit()
