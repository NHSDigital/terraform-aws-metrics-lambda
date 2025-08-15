
resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.name}"
  retention_in_days = 90
  tags = {
    Name = "/aws/lambda/${var.name}"
  }
  kms_key_id = var.logs_kms_key_arn
}

resource "aws_cloudwatch_metric_alarm" "this" {
  count               = length(var.alarm_actions) > 0 ? 1 : 0
  alarm_name          = var.name
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = coalesce(var.alarm_description, "${var.name} invocation error")
  actions_enabled     = true
  alarm_actions       = var.alarm_actions

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  dimensions = {
    FunctionName = aws_lambda_function.this.function_name
  }
}

resource "aws_cloudwatch_event_rule" "this" {
  count               = var.schedule_expression == null ? 0 : 1
  name                = "${var.name}-trigger"
  description         = "${var.name}-trigger"
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "this" {
  count     = var.schedule_expression == null ? 0 : 1
  rule      = aws_cloudwatch_event_rule.this[0].name
  target_id = aws_cloudwatch_event_rule.this[0].name
  arn       = aws_lambda_function.this.arn
}

resource "aws_lambda_permission" "this" {
  count         = var.schedule_expression == null ? 0 : 1
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.this[0].arn
}
