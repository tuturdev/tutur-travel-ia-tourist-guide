variable "region" {
  description = "La región donde se desplegará la infraestructura"
  default     = "us-east-1"
}

variable "s3_bucket_name" {
  description = "Nombre del bucket S3 para almacenar los archivos JSON"
  default     = "0002-tutur-resources"
}
