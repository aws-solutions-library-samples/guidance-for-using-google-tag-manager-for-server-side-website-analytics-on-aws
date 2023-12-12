import aws_cdk as core
import aws_cdk.assertions as assertions

from server_side_tagger.server_side_tagger_stack import ServerSideTaggerStack

# example tests. To run these tests, uncomment this file along with the example
# resource in server_side_tagger/server_side_tagger_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = ServerSideTaggerStack(app, "server-side-tagger")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
