FROM python:3.9-slim

# Instala curl para testes
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app.py .
RUN pip install flask requests

# Define ambiente Kubernetes
ENV K8S_ENV=true

CMD ["python", "app.py"]
