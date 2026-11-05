FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY gateway_server.py start_gateway.py ./

EXPOSE 8080
CMD ["python", "start_gateway.py"]
