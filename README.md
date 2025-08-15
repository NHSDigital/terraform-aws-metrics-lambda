# Terraform AWS Metrics lambda

This is a lambda python implementation heavily based on [YACE](https://github.com/prometheus-community/yet-another-cloudwatch-exporter).

But written in much slower less efficient Python so that it can be packaged as a terraform module and and delivering the output in json to an SQS queue.

YACE and this lambda can be configured to use the [Resource Groups Tagging API](https://docs.aws.amazon.com/resourcegroupstagging/latest/APIReference/overview.html) to discover AWS resources, allowing for scraping metrics relating to dynamic or ephemeral resources.

> **_NOTE:_**
> Be selective about what metrics you scrape, scraping lots of metrics can be expensive, you may want to compare with AWS Cloudwatch Metrics streams, (though that can also be costly as, if not used selectively, it may deliver lots of metrics you are do not need).

> **_NOTE:_**
> Cloudwatch APIs are rate limited, do not deploy multiple metrics lambdas running on the same schedule, the implementation supports environment variables to limit the concurrency for the different APIs e.g. `TAGGING_API_CONCURRENCY` (by account/region)

> **_NOTE:_**
> In the first iteration of this function we're passing the scrape config as a lambda environment variable, there is a total size limit of 4KB for lambda environment variables, if you need more config, the function will need to be updated to support config from s3 or another source.


## variables


| name                          | description                                                                                                                                                                                                    | default   |
|-------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| region                        | region in which the lambda will be deployed, used to select lambda layers                                                                                                                                      | eu-west-2 |
| name                          | lambda function name                                                                                                                                                                                           |           |
| logs_kms_key_arn              | kms_key arn to encrypt the lambda cloudwatch log group, (nb. you'll need to allow cloudwatch access to this kms key)                                                                                           | null      |
| scrape_config                 | json scrape config, see usage below for an example                                                                                                                                                             |           |
| environment                   | additional environment variables for the lambda                                                                                                                                                                | {}        |
| policy_json                   | additional policy json attached to the lambda                                                                                                                                                                  | null      |
| alarm_actions                 | actions to execute if the lambda triggers an ALARM state (e.g. on error), for example this could be an SNS topi arn to publish to                                                                              | []        |
| timeout                       | lambda function timeout in secons, consider this in relation to your schedule expression, if you're trying to scrape a lot of metrics, you may need to scrape less frequently, to avoid overlapping executions | 20        |
| memory_size                   | lambda function memory allocation  in MiB                                                                                                                                                                      | 128       |
| alarm_description             | description for an alarm, if null defaults to `"${var.name} invocation error"`                                                                                                                                 | null      |
| schedule_expression           | metrics collection schedule .. either cron(...) or rate(..) e.g. rate(1 minute), if null the lambda will not be scheduled                                                                                      | null      |
| enable_lambda_insights        | attaches the lambda insights lambda layer                                                                                                                                                                      | false     |
| lambda_insights_layer_version | layer version from https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights-extension-versionsx86-64.html                                                                                | 56        |
| queue_arn                     | SQS queue arn to which the metrics will be delivered                                                                                                                                                           |           |
| queue_url                     | SQS queue url (url or the same queue as the `queue_arn` )                                                                                                                                                      |           |
| max_concurrency               | lambda function max concurrency                                                                                                                                                                                | 1         |

## usage

```hcl

module "aws-metrics" {

  source = "git::https://github.com/NHSDigital/terraform-aws-metrics-lambda?ref=<git-sha>"

  name      = "aws-metrics"
  queue_arn = aws_sqs_queue.aws-metrics.arn
  queue_url = aws_sqs_queue.aws-metrics.url

  timeout = 40

  scrape_config = jsonencode({
    discovery = {
      jobs = [
        {
          type    = "alb"
          regions = ["eu-west-2"]
          search_dimensions = {
            AvailabilityZone = "^$" # exclude az level dimensions
            LoadBalancer     = ".+"
            TargetGroup      = ".+"
          }

          metrics = [
            {
              name  = "HealthyHostCount"
              stats = ["Sum"]
            },
            {
              name  = "UnHealthyHostCount"
              stats = ["Sum"]
            },
            {
              name  = "HTTPCode_Target_2XX_Count"
              stats = ["Sum"]
            },
            {
              name  = "HTTPCode_Target_3XX_Count"
              stats = ["Sum"]
            },
            {
              name  = "HTTPCode_Target_4XX_Count"
              stats = ["Sum"]
            },
            {
              name  = "HTTPCode_Target_5XX_Count"
              stats = ["Sum"]
            }
          ]
        },
        {
          type    = "ecs-containerinsights"
          regions = ["eu-west-2"]
          search_dimensions = {
            ServiceName = ".+"
            ClusterName = ".+"
          }
          metrics = [
            {
              name  = "CpuUtilized"
              stats = ["Maximum"]
            },
            {
              name  = "CpuReserved"
              stats = ["Maximum"]
            },
            {
              name  = "MemoryUtilized"
              stats = ["Maximum"]
            },
            {
              name  = "MemoryReserved"
              stats = ["Maximum"]
            },
            {
              name  = "RunningTaskCount"
              stats = ["Average"]
            },
            {
              name  = "DesiredTaskCount"
              stats = ["Average"]
            },
            {
              name  = "PendingTaskCount"
              stats = ["Average"]
            },
            {
              name  = "NetworkRxBytes"
              stats = ["Average"]
            },
            {
              name  = "NetworkTxBytes"
              stats = ["Average"]
            }
          ]
        },
        {
          type    = "nlb"
          regions = ["eu-west-2"]
          search_dimensions = {
            AvailabilityZone = "^$" # exclude az level dimensions
            LoadBalancer     = ".+"
            TargetGroup      = ".+"
          }

          metrics = [
            {
              name  = "HealthyHostCount"
              stats = ["Sum", "SampleCount"]
            },
            {
              name  = "UnHealthyHostCount"
              stats = ["Sum", "SampleCount"]
            },
            {
              name  = "ActiveFlowCount"
              stats = ["Sum", "SampleCount"]
            }
          ]
        },
        {
          type    = "vpc-endpoint"
          regions = ["eu-west-2"]
          search_dimensions = {
            "Subnet Id" = "^$" # exclude subnet level
          }

          metrics = [
            {
              name  = "ActiveConnections"
              stats = ["Sum", "SampleCount"]
            }
          ]
        },
        {
          type    = "ebs"
          regions = ["eu-west-2"]

          metrics = [
            {
              name  = "VolumeReadBytes"
              stats = ["Sum", "SampleCount"]
            },
            {
              name  = "VolumeWriteBytes"
              stats = ["Sum", "SampleCount"]
            },
            {
              name  = "VolumeReadOps"
              stats = ["Sum", "SampleCount"]
            },
            {
              name  = "VolumeWriteOps"
              stats = ["Sum", "SampleCount"]
            }

          ]
        }
      ]
    }
  })

  schedule_expression = "rate(1 minute)"
  alarm_actions       = [local.resources.sns.alerts.arn]

}

```

## licence
see [LICENCE](LICENCE.md) and as a derivative product of [YACE](https://github.com/prometheus-community/yet-another-cloudwatch-exporter) also, see [APACHE-LICENCE](APACHE-LICENCE.md)

## contributors:
see [CONTRIBUTING](CONTRIBUTING.md)
