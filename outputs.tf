
output "name" {
  description = "The name of the lambda"
  value       = aws_lambda_function.this.function_name
}

output "arn" {
  description = "The lambda's ARN"
  value       = aws_lambda_function.this.arn
}

output "log_group_arn" {
  description = "The cloudwatch log group that the lambda is logging to."
  value       = aws_cloudwatch_log_group.this.arn
}

output "log_group_name" {
  description = "The cloudwatch log group that the lambda is logging to."
  value       = aws_cloudwatch_log_group.this.name
}

output "execution_role" {
  description = "The IAM role ARN and name that the lambda is executing with."
  value = {
    arn  = aws_iam_role.this.arn
    name = aws_iam_role.this.name
  }
}
