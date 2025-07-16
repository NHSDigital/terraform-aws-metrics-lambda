
variable "region" {
  type        = string
  default     = "eu-west-2"
  description = "aws region name"
}

variable "profile" {
  type        = string
  default     = ""
  description = "aws profile name e.g. odin_dev"
}

variable "account" {
  type        = string
  description = "aws account name dev/ptl/prod etc"
}

variable "application" {
  type        = string
  description = "project application"
}

variable "stack" {
  type        = string
  description = "application stack"
}

variable "deployment" {
  type        = string
  description = "deployment name"
}
