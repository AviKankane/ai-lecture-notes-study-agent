from __future__ import annotations

from sqlmodel import Session, select

from ..models import Chapter, Subject


def get_or_create_subject(session: Session, name: str | None) -> Subject | None:
    if not name or not name.strip():
        return None
    clean = name.strip()
    existing = session.exec(select(Subject).where(Subject.name == clean)).first()
    if existing:
        return existing
    subject = Subject(name=clean)
    session.add(subject)
    session.commit()
    session.refresh(subject)
    return subject


def get_or_create_chapter(session: Session, subject: Subject | None, name: str | None) -> Chapter | None:
    if subject is None or not name or not name.strip():
        return None
    clean = name.strip()
    existing = session.exec(
        select(Chapter).where(Chapter.subject_id == subject.id, Chapter.name == clean)
    ).first()
    if existing:
        return existing
    chapter = Chapter(subject_id=subject.id, name=clean)
    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return chapter
