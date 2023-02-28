import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (Stack,
                     aws_iam as iam_,
                     aws_dynamodb as dynamodb_,
                     aws_ec2 as ec2_,
                     aws_ecs as ecs_,
                     aws_apigateway as apigateway,
                     aws_lambda as lambda_)

TESTNET_LIFESPAN = 90*60
TESTNET_MAX_INSTANCES = 3
TOTAL_COUNT_TABLE_ITEM_ID = 'totalCount'
class TestnetFyiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # create vpc w-o nat gw - not needed atm, lowering costs
        vpc = ec2_.Vpc(self, "TestnetVpc",
            nat_gateways=0
        )

        # create dynamodb tables
        # track network creations - network id, createdAt
        # count total networks created

        tableTotalCount = dynamodb_.Table(self, "TestnetTotalCountTable",
            partition_key=dynamodb_.Attribute(name="id", type=dynamodb_.AttributeType.STRING),
            billing_mode=dynamodb_.BillingMode.PAY_PER_REQUEST
        )

        tableNetworkInfo = dynamodb_.Table(self, "TestnetNetworkInfoTable",
            partition_key=dynamodb_.Attribute(name="id", type=dynamodb_.AttributeType.STRING),
            billing_mode=dynamodb_.BillingMode.PAY_PER_REQUEST,
        )

        # define cluster
        ecs_cluster = ecs_.Cluster(self, "TestnetCluster", vpc=vpc)

        # add security group
        sg = ec2_.SecurityGroup(self, 
            "rpc-sg",
            description='security group for rpc',
            vpc=vpc,
            allow_all_outbound=True,
        )

        sg.add_ingress_rule(
            ec2_.Peer.any_ipv4(),
            ec2_.Port.tcp(8545),
            'allow rpc'
        )

        # define container
        task_definition = ecs_.FargateTaskDefinition(self, "TestnetTaskDefinition",
            memory_limit_mib=512, # 512 MiB
            cpu=256 # 0.25 vCPU

        )
        containerName="TestnetContainer"
        container = task_definition.add_container(containerName,
            image=ecs_.ContainerImage.from_registry("ghcr.io/foundry-rs/foundry"),
            logging=ecs_.LogDrivers.aws_logs(stream_prefix="TestnetContainerLog"),
            command=[f'(anvil --host 0.0.0.0) & pid=$!; echo $pid; sleep {TESTNET_LIFESPAN} && kill -HUP $pid']
        )
        container.add_port_mappings(
            ecs_.PortMapping(container_port=8545),
        )

        public_subnets = vpc.select_subnets(subnet_type=ec2_.SubnetType.PUBLIC)

        # define lambda
        handler = lambda_.Function(self, "TestnetCreationHandler",
                    runtime=lambda_.Runtime.PYTHON_3_7,
                    code=lambda_.Code.from_asset("lambda"),
                    handler="create.handler",
                    environment=dict(
                        ECS_CLUSTER_ARN=ecs_cluster.cluster_arn,
                        TASK_DEFINITION_ARN=task_definition.task_definition_arn,
                        TASK_CONTAINER_NAME=containerName,
                        TESTNET_LIFESPAN=str(TESTNET_LIFESPAN),
                        SECURITY_GROUP_ID=sg.security_group_id,
                        PUBLIC_SUBNET_ID=public_subnets.subnet_ids[0],
                        TESTNET_MAX_INSTANCES=str(TESTNET_MAX_INSTANCES),
                        TOTAL_COUNT_TABLE=tableTotalCount.table_name,
                        TOTAL_COUNT_TABLE_ITEM_ID=TOTAL_COUNT_TABLE_ITEM_ID,
                        NETWORK_INFO_TABLE=tableNetworkInfo.table_name
                    ),
                    timeout=cdk.Duration.seconds(60)
        )

        task_definition.grant_run(handler)

        handler.add_to_role_policy(iam_.PolicyStatement(
            effect=iam_.Effect.ALLOW,
            actions=[
                'ecs:ListTasks',
                'ecs:DescribeTasks',
                'ec2:DescribeNetworkInterfaces'
            ],
            resources=[
                '*',
            ],
        ))

        # add permission to write-read dynamo db tables
        tableTotalCount.grant_read_write_data(handler);
        tableNetworkInfo.grant_read_write_data(handler);

        # define api gw
        api = apigateway.RestApi(self, "testnet-api",
                  rest_api_name="Testnet Service",
                  description="This service serves testnets.",
                  default_cors_preflight_options=apigateway.CorsOptions(allow_origins=['*']) 
        )

        # attach api gw to lambda
        lambda_integration = apigateway.LambdaIntegration(handler)
        api.root.add_method("POST", lambda_integration)

        # define another lambda for fetching stats
        # total created

        statsHandler = lambda_.Function(self, "TestnetStats",
                    runtime=lambda_.Runtime.PYTHON_3_7,
                    code=lambda_.Code.from_asset("lambda"),
                    handler="stats.handler",
                    environment=dict(
                        ECS_CLUSTER_ARN=ecs_cluster.cluster_arn,
                        TESTNET_MAX_INSTANCES=str(TESTNET_MAX_INSTANCES),
                        TESTNET_LIFESPAN=str(TESTNET_LIFESPAN),
                        TOTAL_COUNT_TABLE=tableTotalCount.table_name,
                        TOTAL_COUNT_TABLE_ITEM_ID=TOTAL_COUNT_TABLE_ITEM_ID
                    )
        )

        # add permission to read dynamo db tables
        tableTotalCount.grant_read_data(statsHandler);

        # add permission to get active networks
        statsHandler.add_to_role_policy(iam_.PolicyStatement(
            effect=iam_.Effect.ALLOW,
            actions=[
                'ecs:ListTasks',
            ],
            resources=[
                '*',
            ],
        ))

        # attach api gw to lambda
        stats_lambda_integration = apigateway.LambdaIntegration(statsHandler)
        stats_resource = api.root.add_resource("stats")
        stats_resource.add_method("GET", stats_lambda_integration)