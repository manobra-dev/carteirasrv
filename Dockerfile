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

# --so-servir: serve o dashboard_data.json commitado sem rebuscar dados.
# Garante que Railway e PC local mostrem os mesmos números (yfinance total return).
# Para atualizar os dados no Railway, rode ./atualizar_railway.sh localmente.
CMD ["python3", "serve.py", "--sem-browser", "--so-servir"]
