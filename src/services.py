from typing import cast

from model import Service

_SERVICES_CONF: list[dict[str, str | list[str]]] = [
    {"aka": "cwagent", "ns": "CWAgent"},
    {"aka": "usage", "ns": "AWS/Usage"},
    {"aka": "acm", "ns": "AWS/CertificateManager", "rtf": ["acm:certificate"]},
    {
        "aka": "acm-pca",
        "ns": "AWS/ACMPrivateCA",
        "rtf": ["acm-pca:certificate-authority"],
        "rex": ["(?P<PrivateCAArn>.*)"],
    },
    {"aka": "airflow", "ns": "AmazonMWAA", "rtf": ["airflow"]},
    {"aka": "mwaa", "ns": "AWS/MWAA"},
    {
        "aka": "alb",
        "ns": "AWS/ApplicationELB",
        "rtf": [
            "elasticloadbalancing:loadbalancer/app",
            "elasticloadbalancing:targetgroup",
        ],
        "rex": [
            ":(?P<TargetGroup>targetgroup/.+)",
            ":loadbalancer/(?P<LoadBalancer>.+)$",
        ],
    },
    {
        "aka": "appstream",
        "ns": "AWS/AppStream",
        "rtf": ["appstream"],
        "rex": [":fleet/(?P<FleetName>[^/]+)"],
    },
    {"aka": "backup", "ns": "AWS/Backup", "rtf": ["backup"]},
    {
        "aka": "apigateway",
        "ns": "AWS/ApiGateway",
        "rtf": ["apigateway"],
        "rex": [
            "/restapis/(?P<ApiName>[^/]+)$",
            "/restapis/(?P<ApiName>[^/]+)/stages/(?P<Stage>[^/]+)$",
            "/apis/(?P<ApiId>[^/]+)$",
            "/apis/(?P<ApiId>[^/]+)/stages/(?P<Stage>[^/]+)$",
            "/apis/(?P<ApiId>[^/]+)/routes/(?P<Route>[^/]+)$",
        ],
    },
    {
        "aka": "mq",
        "ns": "AWS/AmazonMQ",
        "rtf": ["mq"],
        "rex": ["broker:(?P<Broker>[^:]+)"],
    },
    {"aka": "apprunner", "ns": "AWS/AppRunner"},
    {
        "aka": "appsync",
        "ns": "AWS/AppSync",
        "rtf": ["appsync"],
        "rex": ["apis/(?P<GraphQLAPIId>[^/]+)"],
    },
    {
        "aka": "athena",
        "ns": "AWS/Athena",
        "rtf": ["athena"],
        "rex": ["workgroup/(?P<WorkGroup>[^/]+)"],
    },
    {
        "aka": "asg",
        "ns": "AWS/AutoScaling",
        "rex": ["autoScalingGroupName/(?P<AutoScalingGroupName>[^/]+)"],
    },
    {
        "aka": "beanstalk",
        "ns": "AWS/ElasticBeanstalk",
        "rtf": ["elasticbeanstalk:environment"],
    },
    {"aka": "billing", "ns": "AWS/Billing"},
    {"aka": "cassandra", "ns": "AWS/Cassandra", "rtf": ["cassandra"]},
    {
        "aka": "cloudfront",
        "ns": "AWS/CloudFront",
        "rtf": ["cloudfront:distribution"],
        "rex": ["distribution/(?P<DistributionId>[^/]+)"],
    },
    {
        "aka": "cognito-idp",
        "ns": "AWS/Cognito",
        "rtf": ["cognito-idp:userpool"],
        "rex": ["userpool/(?P<UserPool>[^/]+)"],
    },
    {
        "aka": "datasync",
        "ns": "AWS/DataSync",
        "rtf": ["datasync:task", "datasync:agent"],
        "rex": [":task/(?P<TaskId>[^/]+)", ":agent/(?P<AgentId>[^/]+)"],
    },
    {
        "aka": "ds",
        "ns": "AWS/DirectoryService",
        "rtf": ["ds:directory"],
        "rex": [":directory/(?P<Directory_ID>[^/]+)"],
    },
    {
        "aka": "dms",
        "ns": "AWS/DMS",
        "rtf": ["dms"],
        "rex": [
            "rep:[^/]+/(?P<ReplicationInstanceIdentifier>[^/]+)",
            "task:(?P<ReplicationTaskIdentifier>[^/]+)/(?P<ReplicationInstanceIdentifier>[^/]+)",
        ],
    },
    {
        "aka": "shield",
        "ns": "AWS/DDoSProtection",
        "rtf": ["shield:protection"],
        "rex": ["(?P<ResourceArn>.+)"],
    },
    {
        "aka": "docdb",
        "ns": "AWS/DocDB",
        "rtf": ["rds:db", "rds:cluster"],
        "rex": [
            "cluster:(?P<DBClusterIdentifier>[^/]+)",
            "db:(?P<DBInstanceIdentifier>[^/]+)",
        ],
    },
    {
        "aka": "dx",
        "ns": "AWS/DX",
        "rtf": ["directconnect"],
        "rex": [
            ":dxcon/(?P<ConnectionId>[^/]+)",
            ":dxlag/(?P<LagId>[^/]+)",
            ":dxvif/(?P<VirtualInterfaceId>[^/]+)",
        ],
    },
    {
        "aka": "dynamodb",
        "ns": "AWS/DynamoDB",
        "rtf": ["dynamodb:table"],
        "rex": [":table/(?P<TableName>[^/]+)"],
    },
    {
        "aka": "ebs",
        "ns": "AWS/EBS",
        "rtf": ["ec2:volume"],
        "rex": ["volume/(?P<VolumeId>[^/]+)"],
    },
    {
        "aka": "ec",
        "ns": "AWS/ElastiCache",
        "rtf": ["elasticache:cluster", "elasticache:serverlesscache"],
        "rex": [
            "cluster:(?P<CacheClusterId>[^/]+)",
            "serverlesscache:(?P<clusterId>[^/]+)",
        ],
    },
    {
        "aka": "memorydb",
        "ns": "AWS/MemoryDB",
        "rtf": ["memorydb:cluster"],
        "rex": ["cluster/(?P<ClusterName>[^/]+)"],
    },
    {
        "aka": "ec2",
        "ns": "AWS/EC2",
        "rtf": ["ec2:instance"],
        "rex": ["instance/(?P<InstanceId>[^/]+)"],
    },
    {"aka": "ec2Spot", "ns": "AWS/EC2Spot", "rex": ["(?P<FleetRequestId>.*)"]},
    {
        "aka": "ec2CapacityReservations",
        "ns": "AWS/EC2CapacityReservations",
        "rex": [":capacity-reservation/(?P<CapacityReservationId>)$"],
    },
    {
        "aka": "ecs-svc",
        "ns": "AWS/ECS",
        "rtf": ["ecs:cluster", "ecs:service"],
        "rex": [
            ":cluster/(?P<ClusterName>[^/]+)$",
            ":service/(?P<ClusterName>[^/]+)/(?P<ServiceName>[^/]+)$",
        ],
    },
    {
        "aka": "ecs-containerinsights",
        "ns": "ECS/ContainerInsights",
        "rtf": ["ecs:cluster", "ecs:service"],
        "rex": [
            ":cluster/(?P<ClusterName>[^/]+)$",
            ":service/(?P<ClusterName>[^/]+)/(?P<ServiceName>[^/]+)$",
        ],
    },
    {
        "aka": "containerinsights",
        "ns": "ContainerInsights",
        "rtf": ["eks:cluster"],
        "rex": [":cluster/(?P<ClusterName>[^/]+)$"],
    },
    {
        "aka": "efs",
        "ns": "AWS/EFS",
        "rtf": ["elasticfilesystem:file-system"],
        "rex": ["file-system/(?P<FileSystemId>[^/]+)"],
    },
    {
        "aka": "elb",
        "ns": "AWS/ELB",
        "rtf": ["elasticloadbalancing:loadbalancer"],
        "rex": [":loadbalancer/(?P<LoadBalancerName>.+)$"],
    },
    {
        "aka": "emr",
        "ns": "AWS/ElasticMapReduce",
        "rtf": ["elasticmapreduce:cluster"],
        "rex": ["cluster/(?P<JobFlowId>[^/]+)"],
    },
    {
        "aka": "emr-serverless",
        "ns": "AWS/EMRServerless",
        "rtf": ["emr-serverless:applications"],
        "rex": ["applications/(?P<ApplicationId>[^/]+)"],
    },
    {
        "aka": "es",
        "ns": "AWS/ES",
        "rtf": ["es:domain"],
        "rex": [":domain/(?P<DomainName>[^/]+)"],
    },
    {
        "aka": "firehose",
        "ns": "AWS/Firehose",
        "rtf": ["firehose"],
        "rex": [":deliverystream/(?P<DeliveryStreamName>[^/]+)"],
    },
    {
        "aka": "fsx",
        "ns": "AWS/FSx",
        "rtf": ["fsx:file-system"],
        "rex": ["file-system/(?P<FileSystemId>[^/]+)"],
    },
    {
        "aka": "gamelift",
        "ns": "AWS/GameLift",
        "rtf": ["gamelift"],
        "rex": [":fleet/(?P<FleetId>[^/]+)"],
    },
    {
        "aka": "gwlb",
        "ns": "AWS/GatewayELB",
        "rtf": ["elasticloadbalancing:loadbalancer"],
        "rex": [
            ":(?P<TargetGroup>targetgroup/.+)",
            ":loadbalancer/(?P<LoadBalancer>.+)$",
        ],
    },
    {
        "aka": "ga",
        "ns": "AWS/GlobalAccelerator",
        "rtf": ["globalaccelerator"],
        "rex": [
            "accelerator/(?P<Accelerator>[^/]+)$",
            "accelerator/(?P<Accelerator>[^/]+)/listener/(?P<Listener>[^/]+)$",
            "accelerator/(?P<Accelerator>[^/]+)/listener/(?P<Listener>[^/]+)/endpoint-group/(?P<EndpointGroup>[^/]+)$",
        ],
    },
    {
        "aka": "glue",
        "ns": "Glue",
        "rtf": ["glue:job"],
        "rex": [":job/(?P<JobName>[^/]+)"],
    },
    {
        "aka": "iot",
        "ns": "AWS/IoT",
        "rtf": ["iot:rule", "iot:provisioningtemplate"],
        "rex": [
            ":rule/(?P<RuleName>[^/]+)",
            ":provisioningtemplate/(?P<TemplateName>[^/]+)",
        ],
    },
    {
        "aka": "kafka",
        "ns": "AWS/Kafka",
        "rtf": ["kafka:cluster"],
        "rex": [":cluster/(?P<Cluster_Name>[^/]+)"],
    },
    {
        "aka": "kafkaconnect",
        "ns": "AWS/KafkaConnect",
        "rtf": ["kafka:cluster"],
        "rex": [":connector/(?P<Connector_Name>[^/]+)"],
    },
    {
        "aka": "kinesis",
        "ns": "AWS/Kinesis",
        "rtf": ["kinesis:stream"],
        "rex": [":stream/(?P<StreamName>[^/]+)"],
    },
    {
        "aka": "kinesis-analytics",
        "ns": "AWS/KinesisAnalytics",
        "rtf": ["kinesisanalytics:application"],
        "rex": [":application/(?P<Application>[^/]+)"],
    },
    {
        "aka": "kms",
        "ns": "AWS/KMS",
        "rtf": ["kms:key"],
        "rex": [":key/(?P<KeyId>[^/]+)"],
    },
    {
        "aka": "lambda",
        "ns": "AWS/Lambda",
        "rtf": ["lambda:function"],
        "rex": [":function:(?P<FunctionName>[^/]+)"],
    },
    {
        "aka": "lambdainsights",
        "ns": "LambdaInsights",
        "rtf": ["lambda:function"],
        "rex": [":function:(?P<FunctionName>[^/]+)"],
    },
    {
        "aka": "logs",
        "ns": "AWS/Logs",
        "rtf": ["logs:log-group"],
        "rex": [":log-group:(?P<LogGroupName>.+)"],
    },
    {
        "aka": "mediaconnect",
        "ns": "AWS/MediaConnect",
        "rtf": ["mediaconnect:flow", "mediaconnect:source", "mediaconnect:output"],
        "rex": [
            "^(?P<FlowARN>.*:flow:.*)$",
            "^(?P<SourceARN>.*:source:.*)$",
            "^(?P<OutputARN>.*:output:.*)$",
        ],
    },
    {
        "aka": "mediaconvert",
        "ns": "AWS/MediaConvert",
        "rtf": ["mediaconvert"],
        "rex": ["(?P<Queue>.*:.*:mediaconvert:.*:queues/.*)$"],
    },
    {
        "aka": "mediapackage",
        "ns": "AWS/MediaPackage",
        "rtf": ["mediapackage", "mediapackagev2", "mediapackage-vod"],
        "rex": [
            ":channels/(?P<IngestEndpoint>.+)$",
            ":packaging-configurations/(?P<PackagingConfiguration>.+)$",
        ],
    },
    {
        "aka": "medialive",
        "ns": "AWS/MediaLive",
        "rtf": ["medialive:channel"],
        "rex": [":channel:(?P<ChannelId>.+)$"],
    },
    {
        "aka": "mediatailor",
        "ns": "AWS/MediaTailor",
        "rtf": ["mediatailor:playbackConfiguration"],
        "rex": ["playbackConfiguration/(?P<ConfigurationName>[^/]+)"],
    },
    {
        "aka": "neptune",
        "ns": "AWS/Neptune",
        "rtf": ["rds:db", "rds:cluster"],
        "rex": [
            ":cluster:(?P<DBClusterIdentifier>[^/]+)",
            ":db:(?P<DBInstanceIdentifier>[^/]+)",
        ],
    },
    {
        "aka": "nfw",
        "ns": "AWS/NetworkFirewall",
        "rtf": ["network-firewall:firewall"],
        "rex": ["firewall/(?P<FirewallName>[^/]+)"],
    },
    {
        "aka": "ngw",
        "ns": "AWS/NATGateway",
        "rtf": ["ec2:natgateway"],
        "rex": ["natgateway/(?P<NatGatewayId>[^/]+)"],
    },
    {
        "aka": "nlb",
        "ns": "AWS/NetworkELB",
        "rtf": [
            "elasticloadbalancing:loadbalancer/net",
            "elasticloadbalancing:targetgroup",
        ],
        "rex": [
            ":(?P<TargetGroup>targetgroup/.+)",
            ":loadbalancer/(?P<LoadBalancer>.+)$",
        ],
    },
    {
        "aka": "vpc-endpoint",
        "ns": "AWS/PrivateLinkEndpoints",
        "rtf": ["ec2:vpc-endpoint"],
        "rex": [":vpc-endpoint/(?P<VPC_Endpoint_Id>.+)"],
    },
    {
        "aka": "vpc-endpoint-service",
        "ns": "AWS/PrivateLinkServices",
        "rtf": ["ec2:vpc-endpoint-service"],
        "rex": [":vpc-endpoint-service/(?P<Service_Id>.+)"],
    },
    {"aka": "amp", "ns": "AWS/Prometheus"},
    {
        "aka": "qldb",
        "ns": "AWS/QLDB",
        "rtf": ["qldb"],
        "rex": [":ledger/(?P<LedgerName>[^/]+)"],
    },
    {"aka": "quicksight", "ns": "AWS/QuickSight"},
    {
        "aka": "rds",
        "ns": "AWS/RDS",
        "rtf": ["rds:db", "rds:cluster", "rds:db-proxy"],
        "rex": [
            ":cluster:(?P<DBClusterIdentifier>[^/]+)",
            ":db:(?P<DBInstanceIdentifier>[^/]+)",
            ":db-proxy:(?P<ProxyIdentifier>[^/]+)",
        ],
    },
    {
        "aka": "redshift",
        "ns": "AWS/Redshift-Serverless",
        "rtf": ["redshift-serverless:workgroup", "redshift-serverless:namespace"],
    },
    {
        "aka": "route53-resolver",
        "ns": "AWS/Route53Resolver",
        "rtf": ["route53resolver"],
        "rex": [":resolver-endpoint/(?P<EndpointId>[^/]+)"],
    },
    {
        "aka": "route53",
        "ns": "AWS/Route53",
        "rtf": ["route53"],
        "rex": [":healthcheck/(?P<HealthCheckId>[^/]+)"],
    },
    {"aka": "rum", "ns": "AWS/RUM"},
    {"aka": "s3", "ns": "AWS/S3", "rtf": ["s3"], "rex": ["(?P<BucketName>[^:]+)$"]},
    {"aka": "scheduler", "ns": "AWS/Scheduler"},
    {"aka": "ecr", "ns": "AWS/ECR"},
    {"aka": "timestream", "ns": "AWS/Timestream"},
    {"aka": "secretsmanager", "ns": "AWS/SecretsManager"},
    {"aka": "ses", "ns": "AWS/SES"},
    {
        "aka": "sfn",
        "ns": "AWS/States",
        "rtf": ["states"],
        "rex": ["(?P<StateMachineArn>.*)"],
    },
    {"aka": "sns", "ns": "AWS/SNS", "rtf": ["sns"], "rex": ["(?P<TopicName>[^:]+)$"]},
    {"aka": "sqs", "ns": "AWS/SQS", "rtf": ["sqs"], "rex": ["(?P<QueueName>[^:]+)$"]},
    {
        "aka": "storagegateway",
        "ns": "AWS/StorageGateway",
        "rtf": ["storagegateway"],
        "rex": [
            ":gateway/(?P<GatewayId>[^:]+)$",
            ":share/(?P<ShareId>[^:]+)$",
            "^(?P<GatewayId>[^:/]+)/(?P<GatewayName>[^:]+)$",
        ],
    },
    {"aka": "transfer", "ns": "AWS/Transfer"},
    {
        "aka": "tgw",
        "ns": "AWS/TransitGateway",
        "rtf": ["ec2:transit-gateway"],
        "rex": [
            ":transit-gateway/(?P<TransitGateway>[^/]+)",
            "(?P<TransitGateway>[^/]+)/(?P<TransitGatewayAttachment>[^/]+)",
        ],
    },
    {"aka": "trustedadvisor", "ns": "AWS/TrustedAdvisor"},
    {
        "aka": "vpn",
        "ns": "AWS/VPN",
        "rtf": ["ec2:vpn-connection"],
        "rex": [":vpn-connection/(?P<VpnId>[^/]+)"],
    },
    {
        "aka": "clientvpn",
        "ns": "AWS/ClientVPN",
        "rtf": ["ec2:client-vpn-endpoint"],
        "rex": [":client-vpn-endpoint/(?P<Endpoint>[^/]+)"],
    },
    {
        "aka": "wafv2",
        "ns": "AWS/WAFV2",
        "rtf": ["wafv2"],
        "rex": ["/webacl/(?P<WebACL>[^/]+)"],
    },
    {
        "aka": "workspaces",
        "ns": "AWS/WorkSpaces",
        "rtf": ["workspaces:workspace", "workspaces:directory"],
        "rex": [
            ":workspace/(?P<WorkspaceId>[^/]+)$",
            ":directory/(?P<DirectoryId>[^/]+)$",
        ],
    },
    {
        "aka": "aoss",
        "ns": "AWS/AOSS",
        "rtf": ["aoss:collection"],
        "rex": [":collection/(?P<CollectionId>[^/]+)"],
    },
    {
        "aka": "sagemaker",
        "ns": "AWS/SageMaker",
        "rtf": ["sagemaker:endpoint", "sagemaker:inference-component"],
        "rex": [
            ":endpoint/(?P<EndpointName>[^/]+)$",
            ":inference-component/(?P<InferenceComponentName>[^/]+)$",
        ],
    },
    {
        "aka": "sagemaker-endpoints",
        "ns": "/aws/sagemaker/Endpoints",
        "rtf": ["sagemaker:endpoint"],
        "rex": [":endpoint/(?P<EndpointName>[^/]+)$"],
    },
    {
        "aka": "sagemaker-inference-components",
        "ns": "/aws/sagemaker/InferenceComponents",
        "rtf": ["sagemaker:inference-component"],
        "rex": [":inference-component/(?P<InferenceComponentName>[^/]+)$"],
    },
    {
        "aka": "sagemaker-training",
        "ns": "/aws/sagemaker/TrainingJobs",
        "rtf": ["sagemaker:training-job"],
    },
    {
        "aka": "sagemaker-processing",
        "ns": "/aws/sagemaker/ProcessingJobs",
        "rtf": ["sagemaker:processing-job"],
    },
    {
        "aka": "sagemaker-transform",
        "ns": "/aws/sagemaker/TransformJobs",
        "rtf": ["sagemaker:transform-job"],
    },
    {
        "aka": "sagemaker-inf-rec",
        "ns": "/aws/sagemaker/InferenceRecommendationsJobs",
        "rtf": ["sagemaker:inference-recommendations-job"],
        "rex": [":inference-recommendations-job/(?P<JobName>[^/]+)"],
    },
    {
        "aka": "sagemaker-model-building-pipeline",
        "ns": "AWS/Sagemaker/ModelBuildingPipeline",
        "rtf": ["sagemaker:pipeline"],
        "rex": [":pipeline/(?P<PipelineName>[^/]+)"],
    },
    {
        "aka": "ipam",
        "ns": "AWS/IPAM",
        "rtf": ["ec2:ipam-pool"],
        "rex": [":ipam-pool/(?P<IpamPoolId>[^/]+)$"],
    },
    {"aka": "bedrock", "ns": "AWS/Bedrock"},
    {
        "aka": "event-rule",
        "ns": "AWS/Events",
        "rtf": ["events"],
        "rex": [
            ":rule/(?P<EventBusName>[^/]+)/(?P<RuleName>[^/]+)$",
            ":rule/aws.partner/(?P<EventBusName>.+)/(?P<RuleName>[^/]+)$",
        ],
    },
    {
        "aka": "vpc-lattice",
        "ns": "AWS/VpcLattice",
        "rtf": ["vpc-lattice:service"],
        "rex": [":service/(?P<Service>[^/]+)$"],
    },
    {
        "aka": "networkmanager",
        "ns": "AWS/Network Manager",
        "rtf": ["networkmanager:core-network"],
        "rex": [":core-network/(?P<CoreNetwork>[^/]+)$"],
    },
]


class _Services:

    def __init__(self, services_conf: list[dict[str, str | list[str]]]):
        self._conf_by: dict[str, dict] = {
            cast(str, item["aka"]): item for item in services_conf
        }
        self._conf_by.update({cast(str, item["ns"]): item for item in services_conf})
        self._compiled: dict[str, Service] = {}

    def get(self, ns_or_alias: str) -> Service:
        compiled: Service | None = self._compiled.get(ns_or_alias)
        if not compiled:
            conf = self._conf_by[ns_or_alias]
            compiled = Service(**conf)
            self._compiled[compiled.ns] = compiled
            self._compiled[compiled.aka] = compiled

        return compiled
