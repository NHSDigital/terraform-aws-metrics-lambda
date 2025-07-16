provider "aws" {

  region                      = "eu-west-2"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_region_validation      = true

  access_key = "abc"
  secret_key = "123"

  s3_use_path_style = true

  endpoints {
    cloudwatch     = "http://localhost:5066"
    cloudwatchlogs = "http://localhost:5066"
    cloudtrail     = "http://localhost:5066"
    dynamodb       = "http://localhost:5066"
    firehose       = "http://localhost:5066"
    iam            = "http://localhost:5066"
    kinesis        = "http://localhost:5066"
    lambda         = "http://localhost:5066"
    s3             = "http://localhost:5066"
    secretsmanager = "http://localhost:5066"
    sqs            = "http://localhost:5066"
    ssm            = "http://localhost:5066"
    sns            = "http://localhost:5066"
    events         = "http://localhost:5066"
    ec2            = "http://localhost:5066"
    sts            = "http://localhost:5066"
    kms            = "http://localhost:5066"
  }
}
