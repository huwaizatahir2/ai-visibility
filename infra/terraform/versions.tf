terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state. Create the bucket + lock table once per AWS account, then
  # `terraform init`. One workspace per organization deployment.
  backend "s3" {
    bucket         = "ai-visibility-tfstate"
    key            = "ai-visibility/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "ai-visibility-tflock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "ai-visibility"
      Environment = terraform.workspace
      ManagedBy   = "terraform"
    }
  }
}
