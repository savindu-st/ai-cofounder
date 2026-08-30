FROM python:3.11-slim
WORKDIR /app
COPY shared/ /app/shared/
RUN pip install -e /app/shared/
COPY services/finance/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/finance/app/ /app/app/
CMD ["uvicorn", "app.api.routes:app", "--host", "0.0.0.0", "--port", "8003"]
