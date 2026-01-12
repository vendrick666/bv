"""
Админ-панель API (Управление всеми сущностями)
"""

from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_async_session
from app.core.deps import get_current_admin_user
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.item import Item, Category
from app.models.order import Order, OrderItem, OrderStatus
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["Admin Panel"])


# ==================== SCHEMAS ====================


class AdminUserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole = UserRole.USER


class AdminUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class AdminUserResponse(BaseModel):
    id: int
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0)
    brand: Optional[str] = None
    volume_ml: Optional[int] = Field(None, gt=0)
    stock_quantity: int = Field(default=0, ge=0)
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    owner_id: int
    is_active: bool = True


class AdminItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    brand: Optional[str] = None
    volume_ml: Optional[int] = None
    stock_quantity: Optional[int] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    owner_id: Optional[int] = None
    is_active: Optional[bool] = None


class AdminItemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: Decimal
    brand: Optional[str] = None
    volume_ml: Optional[int] = None
    stock_quantity: int
    image_url: Optional[str] = None
    is_active: bool
    category_id: Optional[int] = None
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class AdminCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AdminCategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    items_count: int = 0

    model_config = {"from_attributes": True}


class AdminOrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    shipping_address: Optional[str] = None
    notes: Optional[str] = None


class OrderItemResponse(BaseModel):
    id: int
    item_id: int
    item_name: str
    quantity: int
    price_at_purchase: Decimal

    model_config = {"from_attributes": True}


class AdminOrderResponse(BaseModel):
    id: int
    order_number: str
    status: OrderStatus
    total_price: Decimal
    shipping_address: Optional[str] = None
    notes: Optional[str] = None
    user_id: int
    user_email: str
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_users: int
    total_items: int
    total_orders: int
    total_categories: int
    active_items: int
    pending_orders: int
    total_revenue: Decimal
    recent_orders: List[AdminOrderResponse]


# ==================== DASHBOARD ====================


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Статистика для дашборда"""
    # Подсчёт пользователей
    total_users = (await session.execute(select(func.count(User.id)))).scalar()

    # Подсчёт товаров
    total_items = (await session.execute(select(func.count(Item.id)))).scalar()
    active_items = (
        await session.execute(
            select(func.count(Item.id)).where(Item.is_active.is_(True))
        )
    ).scalar()

    # Подсчёт заказов
    total_orders = (await session.execute(select(func.count(Order.id)))).scalar()
    pending_orders = (
        await session.execute(
            select(func.count(Order.id)).where(Order.status == OrderStatus.PENDING)
        )
    ).scalar()

    # Подсчёт категорий
    total_categories = (await session.execute(select(func.count(Category.id)))).scalar()

    # Общая выручка
    total_revenue_result = await session.execute(
        select(func.sum(Order.total_price)).where(
            Order.status.in_(
                [OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED]
            )
        )
    )
    total_revenue = total_revenue_result.scalar() or Decimal("0")

    # Последние заказы
    recent_orders_result = await session.execute(
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.item),
        )
        .order_by(Order.created_at.desc())
        .limit(5)
    )
    recent_orders_raw = recent_orders_result.scalars().all()

    recent_orders = []
    for order in recent_orders_raw:
        order_items = [
            OrderItemResponse(
                id=oi.id,
                item_id=oi.item_id,
                item_name=oi.item.name if oi.item else "Deleted",
                quantity=oi.quantity,
                price_at_purchase=oi.price_at_purchase,
            )
            for oi in order.items
        ]
        recent_orders.append(
            AdminOrderResponse(
                id=order.id,
                order_number=order.order_number,
                status=order.status,
                total_price=order.total_price,
                shipping_address=order.shipping_address,
                notes=order.notes,
                user_id=order.user_id,
                user_email=order.user.email if order.user else "Unknown",
                created_at=order.created_at,
                updated_at=order.updated_at,
                items=order_items,
            )
        )

    return DashboardStats(
        total_users=total_users or 0,
        total_items=total_items or 0,
        total_orders=total_orders or 0,
        total_categories=total_categories or 0,
        active_items=active_items or 0,
        pending_orders=pending_orders or 0,
        total_revenue=total_revenue,
        recent_orders=recent_orders,
    )


# ==================== USERS CRUD ====================


@router.get("/users", response_model=List[AdminUserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить список всех пользователей"""
    query = select(User)

    if search:
        query = query.where(
            (User.email.ilike(f"%{search}%"))
            | (User.username.ilike(f"%{search}%"))
            | (User.first_name.ilike(f"%{search}%"))
            | (User.last_name.ilike(f"%{search}%"))
        )

    if role:
        query = query.where(User.role == role)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить пользователя по ID"""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.post(
    "/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED
)
async def create_user(
    data: AdminUserCreate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Создать пользователя"""
    # Проверка уникальности
    existing = await session.execute(
        select(User).where(
            (User.email == data.email) | (User.username == data.username)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email или username уже занят")

    user = User(
        email=data.email,
        username=data.username,
        password_hash=get_password_hash(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        role=data.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: int,
    data: AdminUserUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Обновить пользователя"""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    update_data = data.model_dump(exclude_unset=True)

    # Хеширование пароля если он изменяется
    if "password" in update_data and update_data["password"]:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))
    elif "password" in update_data:
        del update_data["password"]

    for field, value in update_data.items():
        setattr(user, field, value)

    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Удалить пользователя"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить себя")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    await session.delete(user)
    await session.commit()


# ==================== ITEMS CRUD ====================


@router.get("/items", response_model=List[AdminItemResponse])
async def get_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить список всех товаров (включая неактивные)"""
    query = select(Item)

    if search:
        query = query.where(
            (Item.name.ilike(f"%{search}%"))
            | (Item.brand.ilike(f"%{search}%"))
            | (Item.description.ilike(f"%{search}%"))
        )

    if category_id:
        query = query.where(Item.category_id == category_id)

    if is_active is not None:
        query = query.where(Item.is_active == is_active)

    query = query.order_by(Item.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/items/{item_id}", response_model=AdminItemResponse)
async def get_item(
    item_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить товар по ID"""
    result = await session.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return item


@router.post(
    "/items", response_model=AdminItemResponse, status_code=status.HTTP_201_CREATED
)
async def create_item(
    data: AdminItemCreate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Создать товар"""
    item = Item(**data.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.put("/items/{item_id}", response_model=AdminItemResponse)
async def update_item(
    item_id: int,
    data: AdminItemUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Обновить товар"""
    result = await session.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Товар не найден")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await session.commit()
    await session.refresh(item)
    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    hard_delete: bool = Query(False),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Удалить товар (soft или hard delete)"""
    result = await session.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Товар не найден")

    if hard_delete:
        await session.delete(item)
    else:
        item.is_active = False

    await session.commit()


# ==================== CATEGORIES CRUD ====================


@router.get("/categories", response_model=List[AdminCategoryResponse])
async def get_categories(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить список категорий с количеством товаров"""
    result = await session.execute(
        select(Category, func.count(Item.id).label("items_count"))
        .outerjoin(Item, Item.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name)
    )

    categories = []
    for row in result:
        cat = row[0]
        cat.items_count = row[1]
        categories.append(cat)

    return categories


@router.get("/categories/{category_id}", response_model=AdminCategoryResponse)
async def get_category(
    category_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить категорию по ID"""
    result = await session.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    # Подсчёт товаров
    items_count = (
        await session.execute(
            select(func.count(Item.id)).where(Item.category_id == category_id)
        )
    ).scalar()
    category.items_count = items_count or 0

    return category


@router.post(
    "/categories",
    response_model=AdminCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    data: AdminCategoryCreate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Создать категорию"""
    existing = await session.execute(select(Category).where(Category.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Категория уже существует")

    category = Category(**data.model_dump())
    session.add(category)
    await session.commit()
    await session.refresh(category)
    category.items_count = 0
    return category


@router.put("/categories/{category_id}", response_model=AdminCategoryResponse)
async def update_category(
    category_id: int,
    data: AdminCategoryUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Обновить категорию"""
    result = await session.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    await session.commit()
    await session.refresh(category)

    items_count = (
        await session.execute(
            select(func.count(Item.id)).where(Item.category_id == category_id)
        )
    ).scalar()
    category.items_count = items_count or 0

    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Удалить категорию"""
    result = await session.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    # Обнуляем category_id у товаров
    await session.execute(select(Item).where(Item.category_id == category_id))
    items = (
        (await session.execute(select(Item).where(Item.category_id == category_id)))
        .scalars()
        .all()
    )
    for item in items:
        item.category_id = None

    await session.delete(category)
    await session.commit()


# ==================== ORDERS CRUD ====================


@router.get("/orders", response_model=List[AdminOrderResponse])
async def get_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[OrderStatus] = None,
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить список всех заказов"""
    query = select(Order).options(
        selectinload(Order.user), selectinload(Order.items).selectinload(OrderItem.item)
    )

    if status:
        query = query.where(Order.status == status)

    if user_id:
        query = query.where(Order.user_id == user_id)

    query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    orders_raw = result.scalars().all()

    orders = []
    for order in orders_raw:
        order_items = [
            OrderItemResponse(
                id=oi.id,
                item_id=oi.item_id,
                item_name=oi.item.name if oi.item else "Удалён",
                quantity=oi.quantity,
                price_at_purchase=oi.price_at_purchase,
            )
            for oi in order.items
        ]
        orders.append(
            AdminOrderResponse(
                id=order.id,
                order_number=order.order_number,
                status=order.status,
                total_price=order.total_price,
                shipping_address=order.shipping_address,
                notes=order.notes,
                user_id=order.user_id,
                user_email=order.user.email if order.user else "Unknown",
                created_at=order.created_at,
                updated_at=order.updated_at,
                items=order_items,
            )
        )

    return orders


@router.get("/orders/{order_id}", response_model=AdminOrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить заказ по ID"""
    result = await session.execute(
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.item),
        )
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    order_items = [
        OrderItemResponse(
            id=oi.id,
            item_id=oi.item_id,
            item_name=oi.item.name if oi.item else "Удалён",
            quantity=oi.quantity,
            price_at_purchase=oi.price_at_purchase,
        )
        for oi in order.items
    ]

    return AdminOrderResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        total_price=order.total_price,
        shipping_address=order.shipping_address,
        notes=order.notes,
        user_id=order.user_id,
        user_email=order.user.email if order.user else "Unknown",
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=order_items,
    )


@router.put("/orders/{order_id}", response_model=AdminOrderResponse)
async def update_order(
    order_id: int,
    data: AdminOrderUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Обновить заказ"""
    result = await session.execute(
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.item),
        )
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(order, field, value)

    await session.commit()
    await session.refresh(order)

    order_items = [
        OrderItemResponse(
            id=oi.id,
            item_id=oi.item_id,
            item_name=oi.item.name if oi.item else "Удалён",
            quantity=oi.quantity,
            price_at_purchase=oi.price_at_purchase,
        )
        for oi in order.items
    ]

    return AdminOrderResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        total_price=order.total_price,
        shipping_address=order.shipping_address,
        notes=order.notes,
        user_id=order.user_id,
        user_email=order.user.email if order.user else "Unknown",
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=order_items,
    )


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Удалить заказ"""
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    await session.delete(order)
    await session.commit()
