"""
BV Parfume API (Занятие 2)
Объединённый бэкенд + фронтенд
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers


async def init_database():
    """Автоматическая инициализация БД при старте"""
    from sqlalchemy import select
    from passlib.context import CryptContext
    from app.db.database import engine, async_session_maker, Base
    from app.models.user import User, UserRole
    from app.models.item import Item, Category

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Создаём таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        # Проверяем, есть ли уже данные
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            return

        # Создаём админа
        admin = User(
            email="admin@bvparfume.ru",
            username="admin",
            password_hash=pwd_context.hash("Admin123"),
            first_name="Админ",
            role=UserRole.ADMIN,
        )
        session.add(admin)

        # Создаём продавца
        seller = User(
            email="seller@bvparfume.ru",
            username="seller",
            password_hash=pwd_context.hash("Seller123"),
            first_name="Продавец",
            role=UserRole.SELLER,
        )
        session.add(seller)

        # Создаём саппорта
        support = User(
            email="support@bvparfume.ru",
            username="support",
            password_hash=pwd_context.hash("Support123"),
            first_name="Поддержка",
            role=UserRole.SUPPORT,
        )
        session.add(support)
        await session.flush()

        # Категории
        cat1 = Category(name="Женские", description="Женская парфюмерия")
        cat2 = Category(name="Мужские", description="Мужская парфюмерия")
        cat3 = Category(name="Унисекс", description="Универсальные ароматы")
        session.add_all([cat1, cat2, cat3])
        await session.flush()

        # Товары (цены в UZS)
        items = [
            Item(
                name="Chanel No. 5",
                brand="Chanel",
                price=1599000,
                volume_ml=100,
                category_id=cat1.id,
                owner_id=seller.id,
                stock_quantity=50,
                description="Легендарный цветочно-альдегидный аромат.",
                image_url="https://images.unsplash.com/photo-1541643600914-78b084683601?w=400",
            ),
            Item(
                name="Dior Sauvage",
                brand="Dior",
                price=1250000,
                volume_ml=100,
                category_id=cat2.id,
                owner_id=seller.id,
                stock_quantity=50,
                description="Свежий и дикий аромат с нотами бергамота.",
                image_url="https://images.unsplash.com/photo-1594035910387-fea47794261f?w=400",
            ),
            Item(
                name="Bleu de Chanel",
                brand="Chanel",
                price=1390000,
                volume_ml=100,
                category_id=cat2.id,
                owner_id=seller.id,
                stock_quantity=50,
                description="Древесно-ароматический аромат.",
                image_url="https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=400",
            ),
            Item(
                name="Miss Dior",
                brand="Dior",
                price=1150000,
                volume_ml=50,
                category_id=cat1.id,
                owner_id=seller.id,
                stock_quantity=50,
                description="Цветочный шипровый аромат.",
                image_url="https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?w=400",
            ),
            Item(
                name="Tom Ford Oud Wood",
                brand="Tom Ford",
                price=2590000,
                volume_ml=50,
                category_id=cat3.id,
                owner_id=seller.id,
                stock_quantity=50,
                description="Роскошный древесно-удовый аромат.",
                image_url="https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=400",
            ),
            Item(
                name="Versace Eros",
                brand="Versace",
                price=890000,
                volume_ml=100,
                category_id=cat2.id,
                owner_id=seller.id,
                stock_quantity=50,
                description="Страстный аромат с мятой и ванилью.",
                image_url="https://images.unsplash.com/photo-1587017539504-67cfbddac569?w=400",
            ),
            Item(
                name="Lancôme La Vie Est Belle",
                brand="Lancôme",
                price=1050000,
                volume_ml=75,
                category_id=cat1.id,
                owner_id=seller.id,
                stock_quantity=50,
                description="Сладкий ирисово-пралиновый аромат.",
                image_url="https://images.unsplash.com/photo-1595425959155-f1f7da191ef2?w=400",
            ),
            Item(
                name="Creed Aventus",
                brand="Creed",
                price=4500000,
                volume_ml=100,
                category_id=cat2.id,
                owner_id=seller.id,
                stock_quantity=50,
                description="Культовый фруктово-дымный аромат.",
                image_url="https://images.unsplash.com/photo-1590736969955-71cc94901144?w=400",
            ),
        ]
        session.add_all(items)

        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle: startup и shutdown"""
    # Startup
    await init_database()
    yield
    # Shutdown
    from app.db.database import engine

    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API интернет-магазина парфюмерии BV Parfume",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Путь к папке frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# Обработчики ошибок (Занятие 6)
register_exception_handlers(app)

# CORS (Занятие 26)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все для разработки
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health():
    """Проверка здоровья (Занятие 2)"""
    return {"status": "healthy"}


# API роутер - подключаем ПЕРЕД статикой
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Frontend"])
async def serve_index():
    """Главная страница магазина"""
    return FileResponse(FRONTEND_DIR / "index.html")


# Статические файлы из frontend (CSS/JS/images/logo)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Директория для загруженных файлов (локальное хранилище)
UPLOADS_DIR = Path(__file__).parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
