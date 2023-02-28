import json

import time
import os

import logging
import boto3
import decimal

import uuid
from datetime import datetime

client = boto3.client('ecs')
dynamodb = boto3.resource('dynamodb')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

TESTNET_MAX_INSTANCES = int(os.environ['TESTNET_MAX_INSTANCES'])
TESTNET_LIFESPAN = int(os.environ['TESTNET_LIFESPAN'])
TASK_CONTAINER_NAME = os.environ['TASK_CONTAINER_NAME']

def handler(event, context):
    ecs_cluster_arn = os.environ['ECS_CLUSTER_ARN']

    # check limits
    running_tasks = client.list_tasks(
        cluster=ecs_cluster_arn,
    )

    if len(running_tasks['taskArns']) + 1 > TESTNET_MAX_INSTANCES:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            "isBase64Encoded": False,
            'body': f'Reached max limit of testnets (max={TESTNET_MAX_INSTANCES})'
        }

    # verify params
    forkedNetwork = ''
    if event.get('body') is not None:
        params = json.loads(event.get('body'))
        forkedNetwork = params.get('forkedNetwork', '')

    # define command for task
    command = 'anvil --host 0.0.0.0'
    if forkedNetwork == 'mainnet':
        command += ' -f https://cloudflare-eth.com'

    # create task
    task_definition_arn = os.environ['TASK_DEFINITION_ARN']
    subnet_id = os.environ['PUBLIC_SUBNET_ID']
    security_group_id = os.environ['SECURITY_GROUP_ID']

    r = client.run_task(
        cluster=ecs_cluster_arn,
        taskDefinition=task_definition_arn,
        count=1,
        launchType='FARGATE',
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': [
                    subnet_id,
                ],
                'securityGroups': [
                    security_group_id,
                ],
                'assignPublicIp': 'ENABLED'
            }
        },
        overrides={
            'containerOverrides': [
                {
                    'name': TASK_CONTAINER_NAME,
                    'command': [
                        f'({command}) & pid=$!; echo $pid; sleep {TESTNET_LIFESPAN} && kill -HUP $pid',
                    ]
                },
            ]
        }
    )

    logging.info(r)

    taskArn = r['tasks'][0]['taskArn']

    # get endpoint
    rpcEndpoint = ''
    for x in range(0, 12):
        time.sleep(2)
        ts = client.describe_tasks(
            cluster=ecs_cluster_arn,
            tasks=[taskArn]
        )
        logging.info(ts)
        t = ts['tasks'][0]
        if t['attachments'][0]['status'] in ['ATTACHING', 'ATTACHED']:
            details = t['attachments'][0]['details']
            detail = list(filter(lambda d: d['name'] == 'networkInterfaceId', details))[0]
            eni_id = detail['value']
            nis = boto3.client('ec2').describe_network_interfaces(NetworkInterfaceIds=[eni_id])
            pip = nis['NetworkInterfaces'][0]['Association']['PublicIp']
            rpcEndpoint = f'http://{pip}:8545'
            break
    
    if rpcEndpoint == '':
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            "isBase64Encoded": False,
            'body': 'ouch'
        }
    
    created_at = int(datetime.timestamp(datetime.now()))

    # two queries
    # update total count
    # add tracking new networks

    totalCountTable = dynamodb.Table(os.environ['TOTAL_COUNT_TABLE'])

    totalCountTable.update_item(
        Key={
            'id': os.environ['TOTAL_COUNT_TABLE_ITEM_ID']
        },
        UpdateExpression="SET val = if_not_exists(val, :start) + :inc",

        ExpressionAttributeValues={
            ':inc': decimal.Decimal(1),
            ':start': 0,
        },
        ReturnValues="UPDATED_NEW"
    )

    
    networkInfoTable = dynamodb.Table(os.environ['NETWORK_INFO_TABLE'])

    networkInfoTable.put_item(
        Item={
            'id': str(uuid.uuid4()),
            'rpc': rpcEndpoint,
            'created_at': created_at
        }
    )

    # prepare response
    body = {
        'rpc': rpcEndpoint
    }

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        "isBase64Encoded": False,
        'body': json.dumps(body)
    }