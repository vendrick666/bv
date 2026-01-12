FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-dev.txt .
ARG INSTALL_DEV=false
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_DEV" = "true" ] ; then pip install --no-cache-dir -r requirements-dev.txt ; fi

COPY . .

RUN mkdir -p /app/data
RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]
