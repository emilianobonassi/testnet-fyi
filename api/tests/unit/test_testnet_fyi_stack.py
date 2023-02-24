import aws_cdk as core
import aws_cdk.assertions as assertions

from testnet_fyi.testnet_fyi_stack import TestnetFyiStack

# example tests. To run these tests, uncomment this file along with the example
# resource in testnet_fyi/testnet_fyi_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = TestnetFyiStack(app, "testnet-fyi")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
