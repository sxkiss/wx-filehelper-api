# @input: requirements.txt, project source code
# @output: runnable image for wx-filehelper-api
# @position: container build entry for local/CI image creation
# @auto-doc: Update header and folder INDEX.md when this file changes
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["python", "/app/main.py"]
