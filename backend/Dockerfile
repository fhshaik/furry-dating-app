# Stage 1: dependency builder
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: runtime
FROM python:3.12-slim AS runtime

# Create non-root user/group with a real home directory so pip --user packages resolve.
RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -m -s /sbin/nologin appuser

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application source
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Ensure user-installed packages are on PATH and home resolves to the copied site-packages.
ENV HOME=/home/appuser
ENV PATH=/home/appuser/.local/bin:$PATH

EXPOSE 8000

# Healthcheck: use python stdlib so no curl needed
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request, sys; urllib.request.urlopen('http://localhost:8000/health') or sys.exit(1)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
