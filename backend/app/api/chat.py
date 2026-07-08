from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from ..database import get_session
from ..models import ChatMessage, ChatSession
from ..rag.chat_service import answer_question
from ..schemas import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionDetail,
    ChatSessionListItem,
    Citation,
    DeleteSessionResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest):
    return answer_question(request.question, request.lecture_ids, request.session_id)


@router.get("/sessions", response_model=list[ChatSessionListItem])
def list_sessions(session: Session = Depends(get_session)):
    sessions = session.exec(select(ChatSession).order_by(ChatSession.updated_at.desc())).all()
    items: list[ChatSessionListItem] = []
    for chat_session in sessions:
        count = session.exec(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == chat_session.id)
        ).one()
        items.append(
            ChatSessionListItem(
                id=chat_session.id,
                title=chat_session.title,
                lecture_ids=chat_session.lecture_ids_json,
                message_count=count,
                created_at=chat_session.created_at,
                updated_at=chat_session.updated_at,
            )
        )
    return items


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def get_session_detail(session_id: int, session: Session = Depends(get_session)):
    chat_session = session.get(ChatSession, session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    ).all()
    return ChatSessionDetail(
        id=chat_session.id,
        title=chat_session.title,
        lecture_ids=chat_session.lecture_ids_json,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
        messages=[
            ChatMessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                citations=[Citation.model_validate(c) for c in message.citations_json],
                created_at=message.created_at,
            )
            for message in messages
        ],
    )


@router.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
def delete_session(session_id: int, session: Session = Depends(get_session)):
    chat_session = session.get(ChatSession, session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    for message in session.exec(select(ChatMessage).where(ChatMessage.session_id == session_id)).all():
        session.delete(message)
    session.delete(chat_session)
    session.commit()
    return DeleteSessionResponse(deleted=True)
