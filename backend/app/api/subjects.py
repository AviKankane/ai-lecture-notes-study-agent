from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from ..database import get_session
from ..models import Chapter, Lecture, Subject
from ..schemas import ChapterCreate, ChapterResponse, SubjectCreate, SubjectResponse

router = APIRouter(prefix="/subjects", tags=["subjects"])


def _to_response(session: Session, subject: Subject) -> SubjectResponse:
    chapters = session.exec(select(Chapter).where(Chapter.subject_id == subject.id).order_by(Chapter.name)).all()
    count = session.exec(
        select(func.count(Lecture.id)).where(Lecture.subject_id == subject.id)
    ).one()
    return SubjectResponse(
        id=subject.id,
        name=subject.name,
        chapters=[ChapterResponse(id=c.id, subject_id=c.subject_id, name=c.name) for c in chapters],
        lecture_count=count,
    )


@router.get("", response_model=list[SubjectResponse])
def list_subjects(session: Session = Depends(get_session)):
    subjects = session.exec(select(Subject).order_by(Subject.name)).all()
    return [_to_response(session, s) for s in subjects]


@router.post("", response_model=SubjectResponse)
def create_subject(payload: SubjectCreate, session: Session = Depends(get_session)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Subject name is required")
    existing = session.exec(select(Subject).where(Subject.name == name)).first()
    if existing:
        return _to_response(session, existing)
    subject = Subject(name=name)
    session.add(subject)
    session.commit()
    session.refresh(subject)
    return _to_response(session, subject)


@router.post("/{subject_id}/chapters", response_model=ChapterResponse)
def create_chapter(subject_id: int, payload: ChapterCreate, session: Session = Depends(get_session)):
    subject = session.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Chapter name is required")
    existing = session.exec(
        select(Chapter).where(Chapter.subject_id == subject_id, Chapter.name == name)
    ).first()
    if existing:
        return ChapterResponse(id=existing.id, subject_id=existing.subject_id, name=existing.name)
    chapter = Chapter(subject_id=subject_id, name=name)
    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return ChapterResponse(id=chapter.id, subject_id=chapter.subject_id, name=chapter.name)
