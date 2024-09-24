provider "aws" {
  region = "us-east-1"
}

# Crear el bucket S3 para los archivos JSON
resource "aws_s3_bucket" "json_bucket" {
  bucket = var.s3_bucket_name
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
