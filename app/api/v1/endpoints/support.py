"""
API для системы поддержки
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.database import get_async_session
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.support import SupportTicket, SupportMessage, TicketStatus
from app.schemas.support import (
    TicketCreate,
    TicketResponse,
    TicketWithMessages,
    SupportMessageCreate,
    SupportMessageResponse,
    TicketStatusUpdate,
    TicketAssign,
)

router = APIRouter(prefix="/support", tags=["Support"])


def is_staff(user: User) -> bool:
    """Проверка, является ли пользователь сотрудником поддержки"""
    return user.role in [UserRole.SUPPORT, UserRole.ADMIN]


@router.get("/tickets", response_model=List[TicketResponse])
async def get_tickets(
    status_filter: Optional[TicketStatus] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получение тикетов - свои для юзеров, все для саппорта/админа"""
    if is_staff(current_user):
        query = select(SupportTicket).options(
            joinedload(SupportTicket.user), joinedload(SupportTicket.assignee)
        )
    else:
        query = (
            select(SupportTicket)
            .where(SupportTicket.user_id == current_user.id)
            .options(joinedload(SupportTicket.user))
        )

    if status_filter:
        query = query.where(SupportTicket.status == status_filter)

    query = query.order_by(SupportTicket.updated_at.desc())

    result = await session.execute(query)
    tickets = result.unique().scalars().all()

    # Добавляем имена пользователей
    response = []
    for ticket in tickets:
        ticket_dict = {
            "id": ticket.id,
            "subject": ticket.subject,
            "status": ticket.status,
            "user_id": ticket.user_id,
            "user_name": ticket.user.username if ticket.user else None,
            "assigned_to": ticket.assigned_to,
            "assignee_name": ticket.assignee.username if ticket.assignee else None,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
        }
        response.append(ticket_dict)

    return response


@router.post(
    "/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED
)
async def create_ticket(
    data: TicketCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Создание нового тикета"""
    ticket = SupportTicket(
        subject=data.subject,
        user_id=current_user.id,
    )
    session.add(ticket)
    await session.flush()

    # Первое сообщение
    message = SupportMessage(
        content=data.message,
        ticket_id=ticket.id,
        user_id=current_user.id,
        is_staff=is_staff(current_user),
    )
    session.add(message)
    await session.commit()
    await session.refresh(ticket)

    return {
        "id": ticket.id,
        "subject": ticket.subject,
        "status": ticket.status,
        "user_id": ticket.user_id,
        "user_name": current_user.username,
        "assigned_to": ticket.assigned_to,
        "assignee_name": None,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
    }


@router.get("/tickets/{ticket_id}", response_model=TicketWithMessages)
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получение тикета с сообщениями"""
    result = await session.execute(
        select(SupportTicket)
        .where(SupportTicket.id == ticket_id)
        .options(
            joinedload(SupportTicket.messages).joinedload(SupportMessage.user),
            joinedload(SupportTicket.user),
            joinedload(SupportTicket.assignee),
        )
    )
    ticket = result.unique().scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    # Проверка доступа
    if not is_staff(current_user) and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа")

    messages = []
    for msg in ticket.messages:
        messages.append(
            {
                "id": msg.id,
                "content": msg.content,
                "is_staff": msg.is_staff,
                "user_id": msg.user_id,
                "user_name": msg.user.username if msg.user else None,
                "user_role": msg.user.role.value if msg.user else None,
                "created_at": msg.created_at,
            }
        )

    return {
        "id": ticket.id,
        "subject": ticket.subject,
        "status": ticket.status,
        "user_id": ticket.user_id,
        "user_name": ticket.user.username if ticket.user else None,
        "assigned_to": ticket.assigned_to,
        "assignee_name": ticket.assignee.username if ticket.assignee else None,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "messages": messages,
    }


@router.post("/tickets/{ticket_id}/messages", response_model=SupportMessageResponse)
async def add_message(
    ticket_id: int,
    data: SupportMessageCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Добавление сообщения в тикет"""
    result = await session.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    # Проверка доступа
    if not is_staff(current_user) and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа")

    # Проверка, что тикет не закрыт
    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Тикет закрыт")

    message = SupportMessage(
        content=data.content,
        ticket_id=ticket_id,
        user_id=current_user.id,
        is_staff=is_staff(current_user),
    )
    session.add(message)

    # Если саппорт отвечает, меняем статус на "в работе"
    if is_staff(current_user) and ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.IN_PROGRESS

    await session.commit()
    await session.refresh(message)

    return {
        "id": message.id,
        "content": message.content,
        "is_staff": message.is_staff,
        "user_id": message.user_id,
        "user_name": current_user.username,
        "user_role": current_user.role.value,
        "created_at": message.created_at,
    }


@router.put("/tickets/{ticket_id}/status", response_model=TicketResponse)
async def update_ticket_status(
    ticket_id: int,
    data: TicketStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Изменение статуса тикета - только саппорт/админ"""
    if not is_staff(current_user):
        raise HTTPException(status_code=403, detail="Нет прав")

    result = await session.execute(
        select(SupportTicket)
        .where(SupportTicket.id == ticket_id)
        .options(joinedload(SupportTicket.user), joinedload(SupportTicket.assignee))
    )
    ticket = result.unique().scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    ticket.status = data.status
    await session.commit()
    await session.refresh(ticket)

    return {
        "id": ticket.id,
        "subject": ticket.subject,
        "status": ticket.status,
        "user_id": ticket.user_id,
        "user_name": ticket.user.username if ticket.user else None,
        "assigned_to": ticket.assigned_to,
        "assignee_name": ticket.assignee.username if ticket.assignee else None,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
    }


@router.put("/tickets/{ticket_id}/assign", response_model=TicketResponse)
async def assign_ticket(
    ticket_id: int,
    data: TicketAssign,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Назначение тикета на саппорта - только саппорт/админ"""
    if not is_staff(current_user):
        raise HTTPException(status_code=403, detail="Нет прав")

    result = await session.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    # Проверяем, что назначаемый пользователь - саппорт или админ
    assignee_result = await session.execute(
        select(User).where(User.id == data.assigned_to)
    )
    assignee = assignee_result.scalar_one_or_none()

    if not assignee or assignee.role not in [UserRole.SUPPORT, UserRole.ADMIN]:
        raise HTTPException(
            status_code=400, detail="Можно назначить только на саппорта или админа"
        )

    ticket.assigned_to = data.assigned_to
    if ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.IN_PROGRESS

    await session.commit()

    # Перезагружаем с отношениями
    result = await session.execute(
        select(SupportTicket)
        .where(SupportTicket.id == ticket_id)
        .options(joinedload(SupportTicket.user), joinedload(SupportTicket.assignee))
    )
    ticket = result.unique().scalar_one()

    return {
        "id": ticket.id,
        "subject": ticket.subject,
        "status": ticket.status,
        "user_id": ticket.user_id,
        "user_name": ticket.user.username if ticket.user else None,
        "assigned_to": ticket.assigned_to,
        "assignee_name": ticket.assignee.username if ticket.assignee else None,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
    }
