# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Licensed under the Apache License Version 2.0 (the "License"). You may not use this file except
# in compliance with the License. A copy of the License is located at http://www.apache.org/licenses/
# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the
# specific language governing permissions and limitations under the License.
import aws_cdk as core
import aws_cdk.assertions as assertions

from deployment.server_side_tagger_stack import ServerSideTaggerStack

# example tests. To run these tests, uncomment this file along with the example
# resource in server_side_tagger/server_side_tagger_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = ServerSideTaggerStack(app, "server-side-tagger")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
