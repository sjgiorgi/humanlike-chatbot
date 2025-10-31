provider "aws" {
  region = var.aws_region
}

locals {
  fqdn             = "${var.subdomain}.${var.root_domain}"
  s3_frontend_name = "${var.project_name}-${var.project_name}-frontend"
}

# -------------------------
# Route53 hosted zone lookup
# -------------------------
data "aws_route53_zone" "main" {
  name         = var.root_domain
  private_zone = false
}

# -------------------------
# S3 bucket for frontend + OAC policy lock-down
# -------------------------
resource "aws_s3_bucket" "frontend" {
  bucket = local.s3_frontend_name
}

resource "aws_s3_bucket_ownership_controls" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -------------------------
# ACM certificate (us-east-1 required by CloudFront)
# -------------------------
provider "aws" {
  alias  = "use1"
  region = "us-east-1"
}

resource "aws_acm_certificate" "cert" {
  provider          = aws.use1
  domain_name       = local.fqdn
  validation_method = "DNS"
}

resource "aws_route53_record" "cert_validation" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = aws_acm_certificate.cert.domain_validation_options[0].resource_record_name
  type    = aws_acm_certificate.cert.domain_validation_options[0].resource_record_type
  records = [aws_acm_certificate.cert.domain_validation_options[0].resource_record_value]
  ttl     = 300
}

resource "aws_acm_certificate_validation" "cert" {
  provider                = aws.use1
  certificate_arn         = aws_acm_certificate.cert.arn
  validation_record_fqdns = [aws_route53_record.cert_validation.fqdn]
}

# -------------------------
# Elastic Beanstalk (Docker)
# -------------------------
resource "aws_elastic_beanstalk_application" "app" {
  name        = var.project_name
  description = "ChatLab backend EB app"
}

resource "aws_iam_role" "eb_ec2_role" {
  name = "${var.project_name}-eb-ec2-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_instance_profile" "eb_instance_profile" {
  name = "${var.project_name}-eb-instance-profile"
  role = aws_iam_role.eb_ec2_role.name
}

# Minimal EB environment (Docker)
resource "aws_elastic_beanstalk_environment" "env" {
  name                = "${var.project_name}-env"
  application         = aws_elastic_beanstalk_application.app.name
  solution_stack_name = "64bit Amazon Linux 2 v3.9.2 running Docker"

  # Useful defaults: single instance to start
  setting {
    namespace = "aws:autoscaling:asg"
    name      = "MinSize"
    value     = "1"
  }
  setting {
    namespace = "aws:autoscaling:asg"
    name      = "MaxSize"
    value     = "1"
  }
  # Env vars (add your own as needed)
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "DJANGO_SETTINGS_MODULE"
    value     = "generic_chatbot.settings.production"
  }
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "ALLOWED_HOSTS"
    value     = "${local.fqdn},${self.cname}"
  }
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "USE_X_FORWARDED_HOST"
    value     = "True"
  }
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "SECURE_PROXY_SSL_HEADER"
    value     = "HTTP_X_FORWARDED_PROTO, https"
  }

  # Health check that matches your API
  setting {
    namespace = "aws:elb:healthcheck"
    name      = "Interval"
    value     = "10"
  }
  setting {
    namespace = "aws:elb:healthcheck"
    name      = "HealthyThreshold"
    value     = "3"
  }
  setting {
    namespace = "aws:elb:healthcheck"
    name      = "UnhealthyThreshold"
    value     = "5"
  }
  setting {
    namespace = "aws:elb:healthcheck"
    name      = "Timeout"
    value     = "5"
  }
  setting {
    namespace = "aws:elb:healthcheck"
    name      = "Target"
    value     = "HTTP:80/api/health"
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "IamInstanceProfile"
    value     = aws_iam_instance_profile.eb_instance_profile.name
  }
}

# -------------------------
# CloudFront OAC + Distribution (S3 default, EB for /api, /ws)
# -------------------------
resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = "ChatLab-OAC"
  description                       = "OAC for ${local.s3_frontend_name}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  comment             = "ChatLab Distribution"
  aliases             = [local.fqdn]
  default_root_object = "index.html"

  origin {
    origin_id                = "S3-${aws_s3_bucket.frontend.bucket}"
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
  }

  # EB origin (HTTP to keep it simple/robust)
  origin {
    origin_id   = "EB-${aws_elastic_beanstalk_environment.env.name}"
    domain_name = aws_elastic_beanstalk_environment.env.cname
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"  # <— key: CF talks HTTP to EB
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "S3-${aws_s3_bucket.frontend.bucket}"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }

  ordered_cache_behavior {
    path_pattern           = "/api/*"
    target_origin_id       = "EB-${aws_elastic_beanstalk_environment.env.name}"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    compress               = true

    forwarded_values {
      query_string = true
      headers      = ["*"]
      cookies { forward = "all" }
    }
    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  ordered_cache_behavior {
    path_pattern           = "/ws/*"
    target_origin_id       = "EB-${aws_elastic_beanstalk_environment.env.name}"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = false

    forwarded_values {
      query_string = true
      headers      = ["*"]
      cookies { forward = "all" }
    }
    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    acm_certificate_arn            = aws_acm_certificate_validation.cert.certificate_arn
    ssl_support_method             = "sni-only"
    minimum_protocol_version       = "TLSv1.2_2021"
    cloudfront_default_certificate = false
  }
}

# Lock-down bucket to CloudFront (OAC)
data "aws_caller_identity" "me" {}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Sid: "AllowCloudFrontRead",
      Effect: "Allow",
      Principal: { Service: "cloudfront.amazonaws.com" },
      Action: ["s3:GetObject"],
      Resource: "arn:aws:s3:::${aws_s3_bucket.frontend.bucket}/*",
      Condition: {
        StringEquals: {
          "AWS:SourceArn": "arn:aws:cloudfront::${data.aws_caller_identity.me.account_id}:distribution/${aws_cloudfront_distribution.site.id}"
        }
      }
    }]
  })
}

# Route53 A-ALIAS → CloudFront
resource "aws_route53_record" "app_alias" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = local.fqdn
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = "Z2FDTNDATAQYW2" # CloudFront hosted zone ID (global)
    evaluate_target_health = false
  }
}
