#!/usr/bin/env python3
import os

import aws_cdk as cdk

from deployment.server_side_tagger_stack import ServerSideTaggerStack
from deployment.aws_analytics_stack import AWSAnalyticsStack


from cdk_nag import AwsSolutionsChecks, NagSuppressions

app = cdk.App()
server_side_tagger_stack = ServerSideTaggerStack(app, "ServerSideTaggerStack",

    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
        region=os.getenv('CDK_DEFAULT_REGION')
        ),
    description="Guidance for Using Google Tag Manager for Server Side Website Analytics on AWS (SO9262)"
    )

aws_analytics_stack = AWSAnalyticsStack(app, "AWSAnalyticsStack",

    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
        region=os.getenv('CDK_DEFAULT_REGION')
        ),
    apigw=server_side_tagger_stack.apigw_endpoints,
    description="Guidance for Using Google Tag Manager for Server Side Website Analytics on AWS (SO9262)"
    )

NagSuppressions.add_stack_suppressions(
    server_side_tagger_stack,
    [
        {
            "id": "AwsSolutions-IAM5",
            "reason": "AWS managed policies are allowed which sometimes uses * in the resources like - AWSGlueServiceRole has aws-glue-* . AWS Managed IAM policies have been allowed to maintain secured access with the ease of operational maintenance - however for more granular control the custom IAM policies can be used instead of AWS managed policies",
        },
        {
            "id": "AwsSolutions-IAM4",
            "reason": "AWS Managed IAM policies have been allowed to maintain secured access with the ease of operational maintenance - however for more granular control the custom IAM policies can be used instead of AWS managed policies",
        },
        {
            "id": "AwsSolutions-IAM5",
            "reason": "AWS Managed IAM policies have been allowed to maintain secured access with the ease of operational maintenance - however for more granular control the custom IAM policies can be used instead of AWS managed policies",
        },
        {
            "id": "AwsSolutions-S1",
            "reason": "S3 Access Logs are enabled for all data buckets. This stack creates a access log bucket which doesnt have its own access log enabled.",
        },
        {
            "id": "AwsSolutions-SQS3",
            "reason": "SQS queue used in the CDC is a DLQ.",
        },
        {
            "id": "AwsSolutions-SMG4",
            "reason": "Rotation is disabled in the sample code. Customers are encouraged to rotate thirdparty api tokens",
        },
        {
            'id': 'AwsSolutions-KMS5',
            'reason': 'SQS KMS key properties are not accessible from cdk',
        },
         {
            'id': 'AwsSolutions-S10',
            'reason': 'Key properties are not accessible from cdk',
        },
         {
            'id': 'AwsSolutions-L1',
            'reason': 'Key properties are not accessible from cdk',
        },
        {
            'id': 'AwsSolutions-EC23',
            'reason': 'Parameter referencing an intrinsic function',
        },
        {
            'id': 'AwsSolutions-VPC7',
            'reason': 'The VPC does not have an associated Flow Log',
        },
        {
            'id': 'AwsSolutions-ECS4',
            'reason': 'The ECS Cluster has CloudWatch Container Insights disabled',
        },
        {
            'id': 'AwsSolutions-ELB2',
            'reason': 'The ELB does not have access logs enabled',
        },
        {
            'id': 'AwsSolutions-ECS2',
            'reason': 'The ECS Task Definition includes a container definition that directly specifies environment variables',
        },
        {
            'id': 'AwsSolutions-APIG2',
            'reason': 'The REST API does not have request validation enabled.',
        },
        {
            'id': 'AwsSolutions-APIG1',
            'reason': 'The API does not have access logging enabled.',
        },
        {
            'id': 'AwsSolutions-APIG6',
            'reason': 'The REST API Stage does not have CloudWatch logging enabled for all methods.',
        },
        {
            'id': 'AwsSolutions-APIG4',
            'reason': 'The API does not implement authorization.',
        },
        {
            'id': 'AwsSolutions-COG2',
            'reason': 'The Cognito user pool does not require MFA.',
        },
        {
            'id': 'AwsSolutions-KDS3',
            'reason': 'The Kinesis Data Stream specifies server-side encryption and does not use the "aws/kinesis" key',
        },
        {
            'id': 'AwsSolutions-IAM4',
            'reason': 'The managed policy AmazonAPIGatewayPushToCloudWatchLogs is required for apigateway cloud watch logging'
        }
        
    ],
    apply_to_nested_stacks=True
)

NagSuppressions.add_stack_suppressions(
    aws_analytics_stack,
    [
        {
            'id': 'AwsSolutions-KDS3',
            'reason': 'Serverside encryption not enforced in this stack. Stack not intented for production deployment. Called out in the notice',
        },
        {
            'id': 'AwsSolutions-IAM4',
            'reason': 'The managed policy AmazonAPIGatewayPushToCloudWatchLogs is required for apigateway cloud watch logging'
        },
        {
            'id': 'AwsSolutions-IAM5',
            'reason': 'Wild card is to give kinesis firehose access to all prefix in the s3 bucket'
        },
        {
            'id': 'AwsSolutions-KDF1',
            'reason': 'Serverside encryption not enforced in this stack. Stack not intented for production deployment. Called out in the notice',
        },
        {
            'id': 'AwsSolutions-APIG3',
            'reason': 'The REST API stage is not associated with AWS WAFv2 web ACL.',
        },
        {
            'id': 'AwsSolutions-COG2',
            'reason': 'The Cognito user pool does not require MFA.',
        },
        {
            'id': 'AwsSolutions-KDS3',
            'reason': 'The Kinesis Data Stream specifies server-side encryption and does not use the "aws/kinesis" key',
        },
        {
            "id": "AwsSolutions-IAM5",
            "reason": "AWS managed policies are allowed which sometimes uses * in the resources like - AWSGlueServiceRole has aws-glue-* . AWS Managed IAM policies have been allowed to maintain secured access with the ease of operational maintenance - however for more granular control the custom IAM policies can be used instead of AWS managed policies",
        },
        {
            "id": "AwsSolutions-KDF1",
            "reason": "The Kinesis Data Firehose delivery doesn't need server side encryption",
        },
    ],
    apply_to_nested_stacks=True
)

cdk.Aspects.of(app).add(AwsSolutionsChecks())

app.synth()
