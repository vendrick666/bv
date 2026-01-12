"""
Storage service для загрузки файлов (MinIO/S3 + локальный fallback)
"""

import uuid
import json
from datetime import datetime
from typing import Tuple
from pathlib import Path
from io import BytesIO

from fastapi import UploadFile, HTTPException

from app.core.config import settings

# Lazy-loaded MinIO client
_minio_client = None
_use_local_storage = False

# Директория для локального хранения
UPLOADS_DIR = Path("uploads")


def _get_minio_client():
    """Получить или создать MinIO клиент с lazy initialization"""
    global _minio_client, _use_local_storage

    if _use_local_storage:
        return None

    if _minio_client is not None:
        return _minio_client

    try:
        from minio import Minio

        _minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

        # Создаём bucket если не существует
        if not _minio_client.bucket_exists(settings.MINIO_BUCKET):
            _minio_client.make_bucket(settings.MINIO_BUCKET)

            # Устанавливаем публичный доступ на чтение
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{settings.MINIO_BUCKET}/*"],
                    }
                ],
            }
            _minio_client.set_bucket_policy(settings.MINIO_BUCKET, json.dumps(policy))

        print(f"✓ MinIO подключен: {settings.MINIO_ENDPOINT}")
        return _minio_client

    except Exception as e:
        print(f"⚠ MinIO недоступен, используется локальное хранилище: {e}")
        _use_local_storage = True
        UPLOADS_DIR.mkdir(exist_ok=True)
        return None


def _generate_unique_filename(original_filename: str) -> str:
    """Генерация уникального имени файла"""
    ext = Path(original_filename).suffix.lower() if original_filename else ".jpg"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"{timestamp}_{unique_id}{ext}"


def validate_image(file: UploadFile) -> Tuple[bool, str]:
    """Валидация типа и размера изображения"""
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        return (
            False,
            f"Недопустимый тип файла. Разрешены: {', '.join(settings.ALLOWED_IMAGE_TYPES)}",
        )
    return True, ""


async def upload_file(file: UploadFile) -> str:
    """
    Загрузка файла в MinIO или локальное хранилище.
    Возвращает URL для доступа к файлу.
    """
    # Валидация
    is_valid, error = validate_image(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # Читаем содержимое файла
    content = await file.read()

    # Проверка размера
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимум: {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB",
        )

    # Генерируем уникальное имя
    filename = _generate_unique_filename(file.filename)

    # Пробуем MinIO
    client = _get_minio_client()

    if client is not None:
        try:
            client.put_object(
                settings.MINIO_BUCKET,
                filename,
                BytesIO(content),
                length=len(content),
                content_type=file.content_type,
            )

            # Возвращаем MinIO URL
            protocol = "https" if settings.MINIO_SECURE else "http"
            return f"{protocol}://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{filename}"

        except Exception as e:
            print(f"⚠ Ошибка MinIO, сохраняем локально: {e}")

    # Локальное хранилище (fallback)
    UPLOADS_DIR.mkdir(exist_ok=True)
    file_path = UPLOADS_DIR / filename

    with open(file_path, "wb") as f:
        f.write(content)

    return f"/uploads/{filename}"


async def delete_file(url: str) -> bool:
    """Удаление файла по URL"""
    try:
        if url.startswith("/uploads/"):
            # Локальный файл
            filename = url.replace("/uploads/", "")
            file_path = UPLOADS_DIR / filename
            if file_path.exists():
                file_path.unlink()
                return True
        elif settings.MINIO_BUCKET in url:
            # MinIO файл
            client = _get_minio_client()
            if client:
                filename = url.split("/")[-1]
                client.remove_object(settings.MINIO_BUCKET, filename)
                return True
        return False
    except Exception as e:
        print(f"⚠ Ошибка удаления файла: {e}")
        return False


def get_storage_info() -> dict:
    """Информация о текущем хранилище"""
    client = _get_minio_client()
    return {
        "type": "minio" if client else "local",
        "endpoint": settings.MINIO_ENDPOINT if client else str(UPLOADS_DIR.absolute()),
        "bucket": settings.MINIO_BUCKET if client else None,
        "max_size_mb": settings.MAX_UPLOAD_SIZE // (1024 * 1024),
        "allowed_types": settings.ALLOWED_IMAGE_TYPES,
    }
