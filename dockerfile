FROM python:3.9-slim

# Instala o curl para debug
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app.py .
COPY requirements.txt .

RUN pip install -r requirements.txt

# Configura variável para o modo Kubernetes
ENV K8S_ENV=true

CMD ["python", "app.py"]