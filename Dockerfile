FROM python:3.11-slim

WORKDIR /app

# Dependências do sistema (necessário para compilar algumas libs Python)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Railway define a variável PORT automaticamente
EXPOSE 8080

# --sem-yfinance: Yahoo Finance bloqueia IPs de cloud; usa brapi.dev para preços
CMD ["python3", "serve.py", "--sem-browser", "--sem-yfinance"]
