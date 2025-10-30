output "frontend_bucket" { value = aws_s3_bucket.frontend.bucket }
output "rds_endpoint"     { value = aws_db_instance.chatlab_db.address }
output "beanstalk_url"    { value = aws_elastic_beanstalk_environment.env.endpoint_url }
output "cloudfront_domain"{ value = aws_cloudfront_distribution.site.domain_name }
output "site_url"         { value = "https://${local.fqdn}" }
