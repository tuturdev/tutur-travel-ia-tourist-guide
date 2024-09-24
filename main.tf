provider "aws" {
  region = "us-east-1"
}

# Intentar obtener información del bucket existente
data "aws_s3_bucket" "existing_bucket" {
  bucket = "0002-tutur-resources"
}

# Generar un ID aleatorio para garantizar la unicidad del bucket si se crea uno nuevo
resource "random_id" "bucket_id" {
  byte_length = 4
}

# Solo crea el bucket si el bucket "0002-tutur-resources" no existe
resource "aws_s3_bucket" "json_bucket" {
  bucket = "0002-tutur-resources-${random_id.bucket_id.hex}"

  count = length(try([data.aws_s3_bucket.existing_bucket.id], [])) == 0 ? 1 : 0
}

# Definir permisos ACL para el bucket
resource "aws_s3_bucket_acl" "json_bucket_acl" {
  bucket = aws_s3_bucket.json_bucket[0].id
  acl    = "private"

  count = length(try([data.aws_s3_bucket.existing_bucket.id], [])) == 0 ? 1 : 0
}

# Intentar obtener información del rol existente
data "aws_iam_role" "existing_role" {
  name = "tutur_lambda_execution_role"
}

# Definir IAM Role para Lambda si no existe
resource "aws_iam_role" "lambda_exec" {
  count = length(try([data.aws_iam_role.existing_role.id], [])) == 0 ? 1 : 0

  name = "tutur_lambda_execution_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Verificar si la función Lambda ya existe
data "aws_lambda_function" "existing_lambda" {
  function_name = "TuturRAGLambda"
  ignore_errors = true  # Si no existe, ignorar el error
}

# Crear la función Lambda si no existe
resource "aws_lambda_function" "tutur_lambda" {
  count          = length(try([data.aws_lambda_function.existing_lambda.id], [])) == 0 ? 1 : 0
  function_name  = "TuturRAGLambda"
  role           = length(aws_iam_role.lambda_exec) > 0 ? aws_iam_role.lambda_exec[0].arn : data.aws_iam_role.existing_role.arn
  handler        = "lambda_function.lambda_handler"
  runtime        = "python3.12"

  # Sobrescribir el código cada vez
  source_code_hash = filebase64sha256("lambda_function.zip")
  filename         = "lambda_function.zip"

  publish = true
}

# Actualizar el código de la función Lambda si ya existe
resource "aws_lambda_function" "tutur_lambda_update" {
  count = length(try([data.aws_lambda_function.existing_lambda.id], [])) > 0 ? 1 : 0

  function_name  = data.aws_lambda_function.existing_lambda.function_name
  role           = length(aws_iam_role.lambda_exec) > 0 ? aws_iam_role.lambda_exec[0].arn : data.aws_iam_role.existing_role.arn
  handler        = "lambda_function.lambda_handler"
  runtime        = "python3.12"

  # Sobrescribir el código cada vez
  source_code_hash = filebase64sha256("lambda_function.zip")
  filename         = "lambda_function.zip"

  publish = true
}

# API Gateway para exponer el endpoint
resource "aws_api_gateway_rest_api" "tutur_api" {
  name        = "Tutur API"
  description = "API para gestionar los paseos de Tutur"
}

# Crear un archivo local para almacenar el evento JSON de prueba
resource "local_file" "lambda_test_event" {
  content  = <<EOT
{
  "country": "Ecuador",
  "city": "Baños",
  "group": "familia",
  "participants": ["4 adultos"],
  "days": 4,
  "activities": ["Aventura"]
}
EOT
  filename = "${path.module}/lambda_test_event.json"
}

# Invocar la función Lambda con el contenido JSON generado por local_file
resource "aws_lambda_invocation" "lambda_test" {
  function_name = length(aws_lambda_function.tutur_lambda) > 0 ? aws_lambda_function.tutur_lambda[0].function_name : aws_lambda_function.tutur_lambda_update[0].function_name
  input         = local_file.lambda_test_event.content

  # Asegura que se invoca la función solo después de que esté creada
  depends_on = [aws_lambda_function.tutur_lambda, aws_lambda_function.tutur_lambda_update]
}

# Output para mostrar la respuesta de la invocación Lambda
output "lambda_test_result" {
  value = aws_lambda_invocation.lambda_test.result
}
