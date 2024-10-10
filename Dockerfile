# Imagen base de Python
FROM python:3.8-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Exponer el puerto para la aplicación
EXPOSE 8080

# Comando para correr la aplicación usando Uvicorn (FastAPI server)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
