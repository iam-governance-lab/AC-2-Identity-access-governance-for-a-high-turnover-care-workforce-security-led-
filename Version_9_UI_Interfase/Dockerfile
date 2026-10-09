FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SUNHAVEN_HOST=0.0.0.0 SUNHAVEN_PORT=8000 SUNHAVEN_DB_PATH=/data/sunhaven.db
COPY portal/requirements-deploy.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && useradd --uid 10001 --create-home sunhaven && mkdir /data && chown sunhaven:sunhaven /data
COPY --chown=sunhaven:sunhaven portal /app/portal
COPY --chown=sunhaven:sunhaven original /app/original
COPY --chown=sunhaven:sunhaven team_lab/services /app/team_lab/services
WORKDIR /app/portal
USER sunhaven
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"
CMD ["python", "serve.py"]
