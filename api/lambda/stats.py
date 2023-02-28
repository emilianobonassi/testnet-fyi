import json

import os

import logging
import boto3

ecs = boto3.client('ecs')
dynamodb = boto3.resource('dynamodb')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

TESTNET_MAX_INSTANCES = int(os.environ['TESTNET_MAX_INSTANCES'])
TESTNET_LIFESPAN = int(os.environ['TESTNET_LIFESPAN'])

def handler(event, context):
    # get running networks
    ecs_cluster_arn = os.environ['ECS_CLUSTER_ARN']
    running_tasks = ecs.list_tasks(
        cluster=ecs_cluster_arn,
    )

    # get total networks
    table = dynamodb.Table(os.environ['TOTAL_COUNT_TABLE'])

    response = table.get_item(
        Key={
                'id': os.environ['TOTAL_COUNT_TABLE_ITEM_ID']
            }
    )

    if response.get('Item') is None or response.get('Item').get('val') is None:
        totalNetworksCreated = 0
    else:
        totalNetworksCreated = int(response['Item']['val'])

    # prepare response
    body = {
        'totalNetworksCreated': totalNetworksCreated,
        'currentActiveNetworks': len(running_tasks['taskArns']),
        'maxConcurrentNetworks': TESTNET_MAX_INSTANCES,
        'networkLifespan': TESTNET_LIFESPAN
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