"""
Chat endpoints - AI agent interaction
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.models.chat import (
    ChatStartRequest, ChatMessageRequest, ChatResponse, ChatHistoryResponse
)
from src.services.chat_service import ChatService
from src.api.dependencies import get_db, CurrentUser
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat & AI Agent"])


@router.post(
    "/start",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start new chat with AI agent",
    description="Initialize a new conversation session with the service matching agent"
)
def start_chat(
    request: ChatStartRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Start a new chat session.
    
    **Workflow:**
    1. Creates new chat session
    2. If initial message provided, processes it immediately
    3. Returns session ID and agent's first response
    
    **Example:**
    ```json
    {
      "initial_message": "Mujhe kal AC technician chahiye G-13 mein"
    }
    ```
    """
    chat_service = ChatService(db)
    return chat_service.start_chat(current_user, request.initial_message)


@router.post(
    "/message",
    response_model=ChatResponse,
    summary="Send message in chat",
    description="Continue conversation with the AI agent"
)
def send_message(
    request: ChatMessageRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Send message in existing chat session.
    
    **Agent handles:**
    - Intent extraction (service, location, time)
    - Provider search and ranking
    - Provider selection
    - HTL reservation initiation
    
    **Example:**
    ```json
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "message": "Haan pehla provider theek hai"
    }
    ```
    """
    chat_service = ChatService(db)
    
    # Get chat session
    chat = chat_service.get_chat_history(request.session_id, current_user)
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    if not chat.is_active:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Chat session has ended"
        )
    
    return chat_service.process_message(chat, current_user, request.message)


@router.get(
    "/history/{session_id}",
    response_model=ChatHistoryResponse,
    summary="Get chat history",
    description="Retrieve complete chat conversation history"
)
def get_chat_history(
    session_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Get chat history for a session.
    
    Returns all messages, extracted intents, and selected providers.
    """
    from uuid import UUID
    chat_service = ChatService(db)
    
    chat = chat_service.get_chat_history(UUID(session_id), current_user)
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    # Get conversation logs
    from src.database.models import ConversationLog
    logs = db.query(ConversationLog).filter(
        ConversationLog.session_id == UUID(session_id)
    ).order_by(ConversationLog.created_at).all()
    
    return ChatHistoryResponse(
        session_id=chat.session_id,
        user_id=chat.user_id,
        started_at=chat.started_at,
        current_step=chat.current_step,
        is_active=chat.is_active,
        messages=[
            {
                "user_input": log.user_input,
                "agent_response": log.agent_response,
                "agent_name": log.agent_name,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
    )


@router.post(
    "/end/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="End chat session",
    description="Mark chat session as inactive"
)
def end_chat(
    session_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    End an active chat session.
    """
    from uuid import UUID
    chat_service = ChatService(db)
    
    success = chat_service.end_chat(UUID(session_id), current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    return {"message": "Chat ended successfully"}