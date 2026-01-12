"""
API для загрузки файлов (MinIO / локальное хранилище)
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.services.storage import upload_file, delete_file, get_storage_info

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("/image")
async def upload_image(
    file: UploadFile = File(..., description="Изображение для загрузки"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Загрузка изображения.
    Доступно только для продавцов и администраторов.
    """
    # Проверка прав
    if current_user.role not in [UserRole.ADMIN, UserRole.SELLER]:
        raise HTTPException(
            status_code=403,
            detail="Только продавцы и администраторы могут загружать изображения",
        )

    # Загрузка файла
    url = await upload_file(file)

    return {
        "success": True,
        "url": url,
        "filename": file.filename,
        "content_type": file.content_type,
        "message": "Изображение успешно загружено",
    }


@router.delete("/image")
async def delete_image(
    url: str = Query(..., description="URL изображения для удаления"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Удаление изображения по URL.
    Доступно только для продавцов и администраторов.
    """
    # Проверка прав
    if current_user.role not in [UserRole.ADMIN, UserRole.SELLER]:
        raise HTTPException(
            status_code=403,
            detail="Только продавцы и администраторы могут удалять изображения",
        )

    success = await delete_file(url)

    if not success:
        raise HTTPException(status_code=404, detail="Изображение не найдено")

    return {"success": True, "message": "Изображение успешно удалено"}


@router.get("/info")
async def storage_info(current_user: User = Depends(get_current_user)):
    """
    Информация о текущем хранилище.
    """
    return get_storage_info()
