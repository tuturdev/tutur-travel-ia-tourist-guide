provider "aws" {
  region = "us-east-1"
}

# Verifica si el bucket ya existe
data "aws_s3_bucket" "existing_bucket" {
  bucket = "0002-tutur-resources"
  # Esto no fallará si el bucket no existe, simplemente continuará
  count  = length(try([aws_s3_bucket.existing], [])) == 0 ? 1 : 0
}

# Generar un ID aleatorio para garantizar la unicidad del bucket
resource "random_id" "bucket_id" {
  byte_length = 4
}

# Si no existe, crea el bucket con un nombre único
resource "aws_s3_bucket" "json_bucket" {
  bucket = "0002-tutur-resources-${random_id.bucket_id.hex}"
  
  # Crear el bucket solo si el anterior no existe
  count  = length(try([aws_s3_bucket.existing], [])) == 0 ? 1 : 0
}

resource "aws_s3_bucket_acl" "json_bucket_acl" {
  bucket = aws_s3_bucket.json_bucket.id
  acl    = "private"
}

# Crear un Lambda para manejar la API
resource "aws_lambda_function" "tutur_lambda" {
  filename         = "lambda_function.zip"
  function_name    = "TuturRAGLambda"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.8"
  # Puedes omitir source_code_hash temporalmente para evitar el error
  # source_code_hash = filebase64sha256("lambda_function.zip")
}


# API Gateway para exponer el endpoint
resource "aws_api_gateway_rest_api" "tutur_api" {
  name        = "Tutur API"
  description = "API para gestionar los paseos de Tutur"
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
}
