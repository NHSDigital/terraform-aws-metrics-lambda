
variable "region" {
  type        = string
  default     = "eu-west-2"
  description = "aws region name"
}

variable "name" {
  description = "Lambda function name"
  type        = string
}

variable "logs_kms_key_arn" {
  description = "log group kms key encryption"
  type        = string
  default     = null
}

variable "scrape_config" {
  description = "scrape config json"
  type        = string
}

variable "environment" {
  description = "Environment variables for the lambda function"
  type        = map(string)
  default     = {}
}

variable "policy_json" {
  description = "additional policy json attached to the lambda"
  type        = string
  default     = null
}


variable "alarm_actions" {
  description = "The list of actions to execute when this alarm transitions into an ALARM state from any other state. Each action is specified as an Amazon Resource Name (ARN)."
  type        = list(string)
  default     = []
}

variable "timeout" {
  description = "Amount of time your Lambda Function has to run in seconds. Defaults to 3. Max 900 (15 mins)"
  type        = number
  default     = 20
}

variable "memory_size" {
  description = "Amount of memory in MB your Lambda Function can use at runtime."
  type        = number
  default     = 128
}

variable "alarm_description" {
  description = "The description for the cloudwatch metric alarm."
  type        = string
  default     = null
}

variable "schedule_expression" {
  description = "metrics collection schedule .. either cron(...) or rate(..) e.g. rate(1 minute) o"
  type        = string
  default     = null
}

variable "enable_lambda_insights" {
  description = "attaches lambda insights and adds layer"
  type        = bool
  default     = false
}

variable "lambda_insights_layer_version" {
  description = "layer version from https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights-extension-versionsx86-64.html"
  type        = string
  default     = "56"
}

variable "queue_arn" {
  type = string
}

variable "queue_url" {
  type = string
}

variable "max_concurrency" {
  type    = number
  default = 1
}
