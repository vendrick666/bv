#!/usr/bin/env python3
"""
Инициализация БД и добавление тестовых данных
"""
import asyncio
import sys

from sqlalchemy import select

from app.db.database import engine, async_session_maker, Base
from app.models.user import User, UserRole
from app.models.item import Item, Category


def hash_password(password: str) -> str:
    """Простой хеш для инициализации"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)


async def init_db():
    print("Starting DB initialization...")
    
    try:
        # Создаём таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Tables created")
        
        async with async_session_maker() as session:
            # Проверяем, есть ли уже данные
            result = await session.execute(select(User).limit(1))
            if result.scalar_one_or_none():
                print("DB already initialized, skipping...")
                return True
            
            print("Creating users...")
            
            # Создаём админа
            admin = User(
                email="admin@bvparfume.uz",
                username="admin",
                password_hash=hash_password("Admin123"),
                first_name="Админ",
                role=UserRole.ADMIN,
            )
            session.add(admin)
            
            # Создаём продавца
            seller = User(
                email="seller@bvparfume.uz",
                username="seller",
                password_hash=hash_password("Seller123"),
                first_name="Продавец",
                role=UserRole.SELLER,
            )
            session.add(seller)
            
            # Создаём саппорта
            support = User(
                email="support@bvparfume.uz",
                username="support",
                password_hash=hash_password("Support123"),
                first_name="Поддержка",
                role=UserRole.SUPPORT,
            )
            session.add(support)
            await session.flush()
            
            print("Creating categories...")
            
            # Категории
            cat1 = Category(name="Женские", description="Женская парфюмерия")
            cat2 = Category(name="Мужские", description="Мужская парфюмерия")
            cat3 = Category(name="Унисекс", description="Универсальные ароматы")
            session.add_all([cat1, cat2, cat3])
            await session.flush()
            
            print("Creating items...")
            
            # Товары (цены в UZS)
            items = [
                Item(name="Chanel No. 5", brand="Chanel", price=1599000, volume_ml=100, 
                     category_id=cat1.id, owner_id=seller.id, stock_quantity=50,
                     description="Легендарный цветочно-альдегидный аромат.",
                     image_url="https://images.unsplash.com/photo-1541643600914-78b084683601?w=400"),
                Item(name="Dior Sauvage", brand="Dior", price=1250000, volume_ml=100,
                     category_id=cat2.id, owner_id=seller.id, stock_quantity=50,
                     description="Свежий и дикий аромат с нотами бергамота.",
                     image_url="https://images.unsplash.com/photo-1594035910387-fea47794261f?w=400"),
                Item(name="Bleu de Chanel", brand="Chanel", price=1390000, volume_ml=100,
                     category_id=cat2.id, owner_id=seller.id, stock_quantity=50,
                     description="Древесно-ароматический аромат.",
                     image_url="https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=400"),
                Item(name="Miss Dior", brand="Dior", price=1150000, volume_ml=50,
                     category_id=cat1.id, owner_id=seller.id, stock_quantity=50,
                     description="Цветочный шипровый аромат.",
                     image_url="https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?w=400"),
                Item(name="Tom Ford Oud Wood", brand="Tom Ford", price=2590000, volume_ml=50,
                     category_id=cat3.id, owner_id=seller.id, stock_quantity=50,
                     description="Роскошный древесно-удовый аромат.",
                     image_url="https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=400"),
                Item(name="Versace Eros", brand="Versace", price=890000, volume_ml=100,
                     category_id=cat2.id, owner_id=seller.id, stock_quantity=50,
                     description="Страстный аромат с мятой и ванилью.",
                     image_url="https://images.unsplash.com/photo-1587017539504-67cfbddac569?w=400"),
                Item(name="Yves Saint Laurent Libre", brand="Yves Saint Laurent", price=1350000, volume_ml=90, 
                     category_id=cat1.id, owner_id=seller.id, stock_quantity=50, 
                     description="Цветочный аромат с нотами лаванды и апельсинового цвета.", 
                     image_url="https://images.unsplash.com/photo-1590736969955-71cc94801759?w=400"),
                Item(name="Giorgio Armani Acqua di Gio", brand="Giorgio Armani", price=1050000, volume_ml=100, 
                     category_id=cat2.id, owner_id=seller.id, stock_quantity=50, 
                     description="Свежий морской аромат с нотами жасмина и кедра.", 
                     image_url="https://images.unsplash.com/photo-1594035910387-fea47794261f?w=400"),
            ]
            session.add_all(items)
            
            await session.commit()
            print("=" * 50)
            print("DB initialized successfully!")
            print("=" * 50)
            print("Test accounts:")
            print("  Admin:   admin@bvparfume.uz / Admin123")
            print("  Seller:  seller@bvparfume.uz / Seller123")
            print("  Support: support@bvparfume.uz / Support123")
            print("=" * 50)
            return True
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            await engine.dispose()
        except Exception:
            pass


if __name__ == "__main__":
    success = asyncio.run(init_db())
    import sys
    sys.exit(0 if success else 1)
