FROM python:3.11-slim
WORKDIR /app
COPY shared/ /app/shared/
RUN pip install -e /app/shared/
COPY services/business_intelligence/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/business_intelligence/app/ /app/app/
CMD ["uvicorn", "app.api.routes:app", "--host", "0.0.0.0", "--port", "8001"]
