FROM public.ecr.aws/lambda/python:3.12

# Copia las dependencias y el código en el contenedor
COPY requirements.txt ./

# Instala las dependencias
RUN pip install -r requirements.txt

# Copia el código Lambda en el contenedor
COPY lambda_function.py ./

# Comando para ejecutar la Lambda
CMD ["lambda_function.lambda_handler"]

# Cambia algo en el Dockerfile
# Actualizando el contenedor
RUN echo "Actualización de la imagen" > /tmp/update.txt

