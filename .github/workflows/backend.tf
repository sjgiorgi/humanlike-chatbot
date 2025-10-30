terraform {
  backend "s3" {
    bucket         = "chatlab-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "chatlab-locks"
  }
}
