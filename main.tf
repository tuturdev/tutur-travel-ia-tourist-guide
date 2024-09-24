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

  count  = length(try([data.aws_s3_bucket.existing_bucket.id], [])) == 0 ? 1 : 0
}

# Definir permisos ACL para el bucket
resource "aws_s3_bucket_acl" "json_bucket_acl" {
  bucket = aws_s3_bucket.json_bucket[0].id
  acl    = "private"

  count  = length(try([data.aws_s3_bucket.existing_bucket.id], [])) == 0 ? 1 : 0
}

# Definir IAM Role para Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "tutur_lambda_execution_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  count = length(try([data.aws_iam_role.existing_role], [])) == 0 ? 1 : 0
}

# Crear un Lambda para manejar la API
resource "aws_lambda_function" "tutur_lambda" {
  function_name = "TuturRAGLambda"
  role          = aws_iam_role.lambda_exec[0].arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"  # Cambiado a Python 3.12

  # Este bloque permite sobrescribir el código cada vez
  source_code_hash = filebase64sha256("lambda_function.zip")
  filename         = "lambda_function.zip"

  # Crea la función solo si no existe
  count = length(try([aws_lambda_function.tutur_lambda], [])) == 0 ? 1 : 0
}

# API Gateway para exponer el endpoint
resource "aws_api_gateway_rest_api" "tutur_api" {
  name        = "Tutur API"
  description = "API para gestionar los paseos de Tutur"
}
