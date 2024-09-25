# modules/lambda/lambda.tf

# Intentar obtener información de la función Lambda existente
data "aws_lambda_function" "existing_lambda" {
  function_name = "TuturRAGLambda"
}

# Crear un Lambda solo si no existe
resource "aws_lambda_function" "tutur_lambda" {
  count = length(try([data.aws_lambda_function.existing_lambda.id], [])) == 0 ? 1 : 0

  function_name = "TuturRAGLambda"
  role          = aws_iam_role.lambda_exec[0].arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"

  # Sobrescribir el código cada vez
  source_code_hash = filebase64sha256("lambda_function.zip")
  filename         = "lambda_function.zip"

  publish = true
}

# Intentar obtener información del rol existente
data "aws_iam_role" "existing_role" {
  name = "tutur_lambda_execution_role"
}

# Definir IAM Role para Lambda solo si no existe
resource "aws_iam_role" "lambda_exec" {
  count = length(try([data.aws_iam_role.existing_role], [])) == 0 ? 1 : 0
  
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
