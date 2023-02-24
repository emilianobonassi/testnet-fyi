# Testnet.fyi - API

A simple serverless API to spawn a testnet as a serverless container running an [Anvil](https://github.com/foundry-rs/foundry/tree/master/anvil) node

## High level description

A user to create a testnet makes a POST request to an [API Gateway endpoint](https://github.com/emilianobonassi/testnet-fyi/blob/main/api/testnet_fyi/testnet_fyi_stack.py#L82-L90)

The endpoint triggers a [lambda](https://github.com/emilianobonassi/testnet-fyi/blob/main/api/lambda/create.py) which [spawns](https://github.com/emilianobonassi/testnet-fyi/blob/main/api/lambda/create.py#L39-L55) a serverless container via a Fargate task

The container [runs](https://github.com/emilianobonassi/testnet-fyi/blob/main/api/testnet_fyi/testnet_fyi_stack.py#L41-L45) an Anvil node and export the RPC port

The RPC endpoint is [returned](https://github.com/emilianobonassi/testnet-fyi/blob/main/api/lambda/create.py#L91-L104) as payload of the request response

```
{
    'rpc': 'http://<container_ip>:8545'
}
```

Based on [AWS CDK](https://aws.amazon.com/cdk/)

Full stack [here](https://github.com/emilianobonassi/testnet-fyi/blob/main/api/testnet_fyi/testnet_fyi_stack.py)

## Parameters

- [TESTNET_LIFESPAN](https://github.com/emilianobonassi/testnet-fyi/blob/main/api/testnet_fyi/testnet_fyi_stack.py#L10), duration in seconds of a testnet (currently 30 mins)
- [TESTNET_MAX_INSTANCES](https://github.com/emilianobonassi/testnet-fyi/blob/main/api/testnet_fyi/testnet_fyi_stack.py#L11), max concurrent testnets (currently 3)