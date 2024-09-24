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

  # Crear el bucket solo si el bloque de datos "existing_bucket" no encuentra el bucket
  count  = length(try([data.aws_s3_bucket.existing_bucket.id], [])) == 0 ? 1 : 0
}

# Definir permisos ACL para el bucket
resource "aws_s3_bucket_acl" "json_bucket_acl" {
  bucket = aws_s3_bucket.json_bucket[0].id
  acl    = "private"

  # Solo aplica si el bucket fue creado
  count  = length(try([data.aws_s3_bucket.existing_bucket.id], [])) == 0 ? 1 : 0
}

# Verificar si el rol IAM "tutur_lambda_execution_role" ya existe
data "aws_iam_role" "existing_lambda_role" {
  name = "tutur_lambda_execution_role"
}

# Crear el rol IAM solo si no existe
resource "aws_iam_role" "lambda_exec" {
  count = length(try([data.aws_iam_role.existing_lambda_role.id], [])) == 0 ? 1 : 0

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

# Crear un Lambda para manejar la API
resource "aws_lambda_function" "tutur_lambda" {
  filename         = "lambda_function.zip"
  function_name    = "TuturRAGLambda"

  # Utilizamos una expresión condicional para elegir el ARN correcto
  role = length(aws_iam_role.lambda_exec) > 0 ? aws_iam_role.lambda_exec[0].arn : data.aws_iam_role.existing_lambda_role.arn

  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.8"
  # Puedes omitir source_code_hash temporalmente para evitar el error
  # source_code_hash = filebase64sha256("lambda_function.zip")
}

# Política de IAM (solo si se creó el rol)
resource "aws_iam_role_policy" "lambda_exec_policy" {
  count = length(aws_iam_role.lambda_exec)

  name   = "tutur_lambda_policy"
  role   = aws_iam_role.lambda_exec[0].name
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "logs:*",
        Effect = "Allow",
        Resource = "*"
      },
      {
        Action = "s3:*",
        Effect = "Allow",
        Resource = "*"
      }
    ]
  })
}
