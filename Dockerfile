FROM python:3.13-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py healthcheck.py ./
COPY templates/ templates/

ARG APP_VERSION=local
ENV APP_VERSION=${APP_VERSION}
LABEL org.opencontainers.image.revision=${APP_VERSION}

USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=6 \
  CMD ["python", "healthcheck.py"]
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--no-control-socket", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
