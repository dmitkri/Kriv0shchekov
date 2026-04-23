FROM python:3.11-slim

WORKDIR /app

COPY services/anketa_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "services.anketa_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
