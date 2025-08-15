
resource "aws_iam_role" "this" {
  name = "lambda-${var.name}"
  assume_role_policy = jsonencode(
    {
      Version = "2012-10-17",
      Statement = [
        {
          Action = "sts:AssumeRole",
          Principal = {
            Service = "lambda.amazonaws.com"
          },
          Effect = "Allow"
        }
      ]
    }
  )
}

data "aws_iam_policy_document" "this" {

  source_policy_documents = var.policy_json == null ? [] : [var.policy_json]

  statement {
    actions = [
      "tag:GetResources",
      "cloudwatch:GetMetricData",
      "cloudwatch:GetMetricStatistics",
      "cloudwatch:ListMetrics",
      "apigateway:GET",
      "aps:ListWorkspaces",
      "autoscaling:DescribeAutoScalingGroups",
      "dms:DescribeReplicationInstances",
      "dms:DescribeReplicationTasks",
      "ec2:DescribeTransitGatewayAttachments",
      "ec2:DescribeSpotFleetRequests",
      "shield:ListProtections",
      "storagegateway:ListGateways",
      "storagegateway:ListTagsForResource",
      "iam:ListAccountAliases",
      "iam:GetAccountAlias",
      "sts:GetCallerIdentity"
    ]
    resources = [
      "*"
    ]
  }

  statement {
    effect        = "Allow"
    not_actions   = []
    not_resources = []
    actions = [
      "logs:PutLogEvents",
      "logs:CreateLogStream"
    ]
    resources = [
      aws_cloudwatch_log_group.this.arn,
      "${aws_cloudwatch_log_group.this.arn}:*"
    ]
  }

  statement {
    effect        = "Allow"
    not_actions   = []
    not_resources = []
    actions = [
      "sqs:SendMessage",
      "sqs:SendMessageBatch",
      "sqs:GetQueueAttributes"
    ]
    resources = [
      var.queue_arn
    ]
  }

}

resource "aws_iam_role_policy" "this" {
  name = var.name
  role = aws_iam_role.this.id

  policy = data.aws_iam_policy_document.this.json
}

resource "aws_iam_role_policy_attachment" "insights" {
  count      = var.enable_lambda_insights ? 1 : 0
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"
}
