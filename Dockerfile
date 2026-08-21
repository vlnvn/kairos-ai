FROM python:3.12.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN addgroup --system kairos && adduser --system --ingroup kairos kairos

COPY pyproject.toml ./
COPY src ./src
COPY static ./static
COPY artifacts/kairos_final.cbm ./artifacts/kairos_final.cbm

RUN python -m pip install --no-cache-dir --disable-pip-version-check .

USER kairos
EXPOSE 8080

CMD ["python", "-m", "kairos_ai.server", "--host", "0.0.0.0", "--port", "8080"]
