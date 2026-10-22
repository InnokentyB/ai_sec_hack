FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --gid 10001 appuser && useradd --uid 10001 --gid 10001 --create-home appuser
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock && playwright install --with-deps chromium && chmod -R a+rX /root/.cache && mv /root/.cache/ms-playwright /opt/browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps .
COPY cli ./cli
COPY tests ./tests
RUN mkdir /data /artifacts /provision && chown appuser:appuser /data /artifacts /provision
USER appuser:appuser
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
