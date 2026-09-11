# Production image for the FastAPI backend. Built and run by
# docker-compose.prod.yml (locally or on the Hostinger VPS) and by the
# GitHub Actions deploy workflows — see docs/deploying-to-hostinger.pdf for
# the full walkthrough.
#
# Deliberately runs uvicorn WITHOUT --reload: on this project's Windows dev
# machine, --reload's multiprocessing-based worker has been observed to
# leave an orphaned process holding the listening socket with stale code
# after being killed (see CLAUDE.md's "Gotchas" section) — the same
# process-per-worker model is used on Linux, so production never uses
# --reload and restarts the container instead when new code is deployed.

FROM python:3.14-slim

WORKDIR /app

# Install dependencies first so this layer is cached unless
# requirements.txt actually changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend application code.
COPY . .

EXPOSE 8020

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8020"]
