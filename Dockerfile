# Usamos la versión oficial de Python 3.13 (ligera)
FROM python:3.13-slim

# Configuraciones de entorno para que Python no guarde caché y los logs salgan directo en la consola
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Creamos la carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copiamos primero los requerimientos para aprovechar la caché de Docker
COPY requirements.txt .

# Instalamos las librerías
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el resto del código fuente al contenedor
COPY . .

# Exponemos el puerto que usa FastAPI por defecto
EXPOSE 8000

# Comando para arrancar el servidor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
