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
