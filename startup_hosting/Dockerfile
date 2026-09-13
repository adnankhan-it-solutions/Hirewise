FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends clamav-client postgresql-client curl && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 hirewise
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/
RUN python manage.py collectstatic --noinput && chown -R hirewise:hirewise /app
USER hirewise
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--access-logfile", "/dev/null"]
