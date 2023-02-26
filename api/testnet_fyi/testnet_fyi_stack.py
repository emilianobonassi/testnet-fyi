import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (Stack,
                     aws_iam as iam_,
                     aws_ec2 as ec2_,
                     aws_ecs as ecs_,
                     aws_apigateway as apigateway,
                     aws_lambda as lambda_)

TESTNET_LIFESPAN = 90*60
TESTNET_MAX_INSTANCES = 3
class TestnetFyiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # create vpc w-o nat gw - not needed atm, lowering costs
        vpc = ec2_.Vpc(self, "TestnetVpc",
            nat_gateways=0
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
        container = task_definition.add_container("TestnetContainer",
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
                        SECURITY_GROUP_ID=sg.security_group_id,
                        PUBLIC_SUBNET_ID=public_subnets.subnet_ids[0],
                        TESTNET_MAX_INSTANCES=str(TESTNET_MAX_INSTANCES)
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

        # define api gw
        api = apigateway.RestApi(self, "testnet-api",
                  rest_api_name="Testnet Service",
                  description="This service serves testnets.",
                  default_cors_preflight_options=apigateway.CorsOptions(allow_origins=['*']) 
        )

        # attach api gw to lambda
        lambda_integration = apigateway.LambdaIntegration(handler)
        api.root.add_method("POST", lambda_integration)
