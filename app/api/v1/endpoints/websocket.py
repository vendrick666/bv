"""
WebSocket чат (Занятия 30-32)
"""

from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select

from app.db.database import async_session_maker
from app.core.security import decode_token
from app.models.user import User
from app.models.message import Message

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    Менеджер соединений (Занятие 31)

    ВАЖНО: In-memory подход работает только для одного инстанса!
    При горизонтальном масштабировании нужен Redis Pub/Sub
    """

    def __init__(self):
        # {item_id: {user_id: websocket}}
        self.connections: Dict[int, Dict[int, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int, item_id: int):
        await websocket.accept()
        if item_id not in self.connections:
            self.connections[item_id] = {}
        self.connections[item_id][user_id] = websocket

    def disconnect(self, user_id: int, item_id: int):
        if item_id in self.connections:
            self.connections[item_id].pop(user_id, None)

    async def send_to_user(self, message: dict, user_id: int, item_id: int):
        if item_id in self.connections and user_id in self.connections[item_id]:
            await self.connections[item_id][user_id].send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/chat/{item_id}")
async def websocket_chat(
    websocket: WebSocket,
    item_id: int,
    token: str = Query(...),
):
    """
    WebSocket для чата по товару (Занятия 30-32)

    Подключение: ws://localhost:8000/ws/chat/123?token=JWT_TOKEN
    """
    # Аутентификация
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    user_id = int(payload.get("sub"))

    async with async_session_maker() as session:
        # Проверяем пользователя
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            await websocket.close(code=4001)
            return

        await manager.connect(websocket, user_id, item_id)

        # Загрузка истории (Занятие 32)
        history_result = await session.execute(
            select(Message)
            .where(Message.item_id == item_id)
            .order_by(Message.timestamp.desc())
            .limit(50)
        )
        messages = history_result.scalars().all()

        await websocket.send_json(
            {
                "type": "history",
                "messages": [
                    {
                        "id": m.id,
                        "sender_id": m.sender_id,
                        "text": m.text,
                        "timestamp": m.timestamp.isoformat(),
                    }
                    for m in reversed(messages)
                ],
            }
        )

        try:
            while True:
                data = await websocket.receive_json()
                text = data.get("text", "").strip()
                receiver_id = data.get("receiver_id")

                if not text or not receiver_id:
                    continue

                # Сохраняем сообщение (Занятие 32)
                msg = Message(
                    sender_id=user_id,
                    receiver_id=receiver_id,
                    item_id=item_id,
                    text=text,
                )
                session.add(msg)
                await session.commit()
                await session.refresh(msg)

                message_data = {
                    "type": "message",
                    "id": msg.id,
                    "sender_id": user_id,
                    "text": text,
                    "timestamp": msg.timestamp.isoformat(),
                }

                # Отправляем получателю
                await manager.send_to_user(message_data, receiver_id, item_id)

                # Подтверждение отправителю
                await websocket.send_json({"type": "sent", **message_data})

        except WebSocketDisconnect:
            manager.disconnect(user_id, item_id)
