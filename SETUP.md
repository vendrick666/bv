# Запуск BV Parfume

## 🐳 Через Docker (РЕКОМЕНДУЕТСЯ)

**Один раз и всё работает:**

```bash
cd bv_parfume
docker-compose up --build
```

Готово! Открой http://localhost:3000

### Тестовые аккаунты:
- **Админ:** admin@bvparfume.ru / Admin123
- **Продавец:** seller@bvparfume.ru / Seller123

### Полезные команды:
```bash
# Запуск в фоне
docker-compose up -d --build

# Остановка
docker-compose down

# Логи
docker-compose logs -f

# Пересборка
docker-compose up --build --force-recreate

# Прогон тестов в контейнере (устанавливает dev-зависимости)
docker-compose up --build --abort-on-container-exit --exit-code-from backend-test backend-test
# Или запустить тестовый контейнер и выполнить команду вручную:
docker-compose run --rm --service-ports backend-test pytest -q
```

---

## 💻 Локальный запуск (без Docker)

```bash
cd bv_parfume

# Виртуальное окружение
python -m venv venv
venv\Scripts\activate

# Зависимости
pip install -r requirements.txt

# Инициализация БД с тестовыми данными
python init_db.py

# Запуск бэкенда
uvicorn app.main:app --reload
```

Фронтенд открой отдельно: `frontend/index.html`

---

## 📍 Адреса

| Сервис | URL |
|--------|-----|
| Фронтенд | http://localhost:3000 |
| API Docs | http://localhost:3000/docs |
| Backend (напрямую) | http://localhost:8000 |
