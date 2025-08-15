locals {
  lambda_layers = concat(
    ["arn:aws:lambda:${var.region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python312-x86_64:15"],
    var.enable_lambda_insights ?
    ["arn:aws:lambda:${var.region}:580247275435:layer:LambdaInsightsExtension:${var.lambda_insights_layer_version}"]
    : []
  )

  environment = merge(
    var.environment,
    {
      QUEUE_URL     = var.queue_url
      SCRAPE_CONFIG = var.scrape_config
    }
  )

}

data "archive_file" "this" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/${var.name}.zip"
  excludes    = ["**/__pycache__/*"]

}

# tfsec:ignore:aws-lambda-enable-tracing
resource "aws_lambda_function" "this" {
  filename = data.archive_file.this.output_path

  function_name    = var.name
  role             = aws_iam_role.this.arn
  handler          = "function.handler"
  runtime          = "python3.12"
  source_code_hash = data.archive_file.this.output_base64sha256

  reserved_concurrent_executions = var.max_concurrency

  layers      = local.lambda_layers
  timeout     = var.timeout
  memory_size = var.memory_size

  environment {
    variables = local.environment
  }

  depends_on = [
    aws_cloudwatch_log_group.this,
    data.archive_file.this
  ]

}
