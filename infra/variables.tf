variable "aws_region"         { default = "us-east-1" }
variable "project_name"       { default = "chatlab" }

# DB creds
variable "db_username" {}
variable "db_password" {}

# Domain info (hosted zone must already exist in Route 53)
variable "root_domain" { description = "Base domain in Route53, e.g., your-research-lab.com" }
variable "subdomain" {
  description = "Subdomain to host ChatLab, e.g., chatlab"
  default     = "chatlab"
}
