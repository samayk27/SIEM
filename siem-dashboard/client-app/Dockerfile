FROM python:3.14-slim

WORKDIR /app
COPY client-app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY client-app/ .

EXPOSE 7357
CMD ["python", "app.py"]
