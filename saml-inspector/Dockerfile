FROM python:3.12-slim

# pysaml2 shells out to `xmlsec1` for signature ops; libxmlsec1-openssl
# and libxml2 headers are required for the lxml wheel.
RUN apt-get update && apt-get install -y --no-install-recommends \
        xmlsec1 \
        libxmlsec1-openssl \
        libxml2 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "app:app"]
