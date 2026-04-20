FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

# The MCR image ships browsers + OS deps; pip-install the matching
# Playwright Python wheel on top.
RUN pip install --no-cache-dir playwright==1.47.0

COPY capture.py .

# Output directory mounted by compose.
ENV OUT_DIR=/out

CMD ["python", "capture.py"]
