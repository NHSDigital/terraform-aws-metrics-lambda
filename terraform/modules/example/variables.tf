variable "shared" {
  type = any
  # type = object({
  #   account = string
  #   account_id = string
  #   account_name = string
  #   account-ids = map(string)
  #   amazon_emr_bucket_arns = list(string)
  #   amazon_repo_bucket_arns = list(string)
  #   amazon_ssm_bucket_arns = list(string)
  #   aws_ecr_bucket_arn = string
  #   base_account_name = string
  #   base_arn = map(string)
  #   base_dns_name = string
  #   boto_env_vars = map(string)
  #   codebuild-runner-bucket-arn = string
  #   ecr_registry = string
  #   iam_code_artifact_read_packages = list(string)
  #   iam_code_artifact_read_write_packages = list(string)
  #   iam_dynamodb_full_read_write_access = list(string)
  #   iam_dynamodb_get_put_update_access = list(string)
  #   iam_dynamodb_query_access = list(string)
  #   iam_dynamodb_read_only_access = list(string)
  #   iam_dynamodb_read_stream_actions = list(string)
  #   iam_dynamodb_read_write_access = list(string)
  #   iam_dynamodb_update_item_access = list(string)
  #   iam_ecr_get_authorisation_token = list(string)
  #   iam_ecr_pull_images = list(string)
  #   iam_ecr_pull_push_images = list(string)
  #   iam_kms_decrypt_actions = list(string)
  #   iam_kms_encrypt_actions = list(string)
  #   iam_kms_encrypt_decrypt_actions = list(string)
  #   iam_lambda_invoke_function = list(string)
  #   iam_s3_delete_actions = list(string)
  #   iam_s3_delete_version_actions = list(string)
  #   iam_s3_list_bucket_actions = list(string)
  #   iam_s3_put_actions = list(string)
  #   iam_s3_read_only_actions = list(string)
  #   iam_s3_read_write_actions = list(string)
  #   iam_s3_read_write_no_delete_actions = list(string)
  #   iam_secretsmanager_create_actions = list(string)
  #   iam_secretsmanager_delete_actions = list(string)
  #   iam_secretsmanager_get_put_actions = list(string)
  #   iam_secretsmanager_list_actions = list(string)
  #   iam_secretsmanager_put_actions = list(string)
  #   iam_secretsmanager_read_actions = list(string)
  #   iam_sns_publish_access = list(string)
  #   iam_sqs_read_actions = list(string)
  #   iam_sqs_read_write_actions = list(string)
  #   iam_sqs_write_actions = list(string)
  #   iam_ssm_get_parameter_actions = list(string)
  #   iam_ssm_get_put_parameter_actions = list(string)
  #   is_dev = bool
  #   is_not_prod = bool
  #   is_prod = bool
  #   is_ptl = bool
  #   nhs_digital_cidrs = list(string)
  #   pen_test_cidrs = list(string)
  #   region = string
  #   splunk_hec_public_ips = list(string)
  # })
}

# tflint-ignore: terraform_unused_declarations
variable "account_vpc" {
  description = "account module vpc composite output"
  type = object({
    azs  = set(string),
    cidr = string
    ecs  = object({ id = string, name = string }),
    eks = object({
      efs           = object({ fs-id = string, sg-id = string }),
      endpoint      = string,
      id            = string,
      name          = string,
      oidc_provider = object({ arn = string, url = string }),
      roles         = map(object({ arn = string, name = string })),
      sg_id         = string,
    }),
    gateway-prefix-list-ids   = map(string)
    id                        = string
    interface-endpoint-sg-ids = map(string)
    nacls                     = map(object({ arn = string, id = string }))
    private_dns               = object({ name = string, zone_id = string })
    public_dns                = object({ name = string, zone_id = string })
    region                    = string
    sd                        = object({ id = string, name = string })
    subnet = map(map(object({
      arn = string, availability_zone = string, cidr_block = string, id = string, route_table_id = string
    })))
  })

}

# tflint-ignore: terraform_unused_declarations
variable "resources" {
  description = "account module resources composite output"
  type = object(
    {
      acm : map(object({ arn : string, name : string })),
      kms : map(object({ alias : optional(string), arn : string, id : string })),
      lambda : map(object({ arn : string, name : string })),
      roles : map(object({ arn : string, name : string })),
      s3 : map(object({ arn : string, bucket : string, kms : optional(string) })),
      sns : map(object({ arn : string, name : string })),
    }
  )

}

variable "example" {
  type = string
}
