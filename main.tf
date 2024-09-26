provider "aws" {
  region = "us-east-1"
}

# Incluir los módulos y recursos
module "lambda_module" {
  source = "./modules/lambda"
}

module "s3_bucket_module" {
  source = "./modules/s3_bucket"
}

module "api_gateway_module" {
  source = "./modules/api_gateway"
}


# Archivo JSON para test
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

# Invocar la función Lambda para test usando el output del módulo lambda_module
resource "aws_lambda_invocation" "lambda_test" {
  function_name = module.lambda_module.lambda_function_name
  input         = file("${local_file.lambda_test_event.filename}")

  depends_on = [module.lambda_module]
}

# Mostrar el resultado del test
output "lambda_test_result" {
  value = aws_lambda_invocation.lambda_test.result
}