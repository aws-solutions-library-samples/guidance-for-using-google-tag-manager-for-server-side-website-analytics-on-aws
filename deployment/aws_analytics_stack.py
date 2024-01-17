import os

from aws_cdk import (
    Stack,
    StackProps,
    aws_certificatemanager as acm,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_logs as logs,
    aws_cognito as cognito,
    aws_kinesis as kds,
    aws_kinesisfirehose as kinesisfirehose,
    aws_glue as glue,
    aws_athena as athena,
    aws_quicksight as quicksight,
    aws_elasticsearch as elasticsearch0,
    RemovalPolicy
)
from aws_solutions_constructs.aws_kinesis_streams_kinesis_firehose_s3 import KinesisStreamsToKinesisFirehoseToS3 
from deployment.server_side_tagger_stack import ServerSideTaggerStack

from constructs import Construct
import json

DIRNAME = os.path.dirname(__file__)

class AWSAnalyticsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, apigw, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # account and region
        acc = os.getenv('CDK_DEFAULT_ACCOUNT')
        region = os.getenv('CDK_DEFAULT_REGION')
        #creating Acess log group
        access_logs=logs.LogGroup(self, "ApiGatewayAccessLogs")
        stream_name = "gtagStream"

        #creating role to execute API
        api_role=iam.Role(self,'gtagRole', assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"))
        api_role.add_managed_policy(iam.ManagedPolicy.from_managed_policy_arn(self, 'AmazonAPIGatewayInvokeFullAccessArn', 'arn:aws:iam::aws:policy/AmazonAPIGatewayInvokeFullAccess'))

        log_group_arn = access_logs.log_group_arn
        
        #creating cloudwatch role
        cloud_watch_role = iam.Role(self,'cloudWatchRole', 
                                    assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"))
        cloud_watch_role.add_managed_policy(iam.ManagedPolicy.from_managed_policy_arn(self,"cwMgPolicyArn","arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"))
        account=apigateway.CfnAccount(self, 'cfnAccount', cloud_watch_role_arn=cloud_watch_role.role_arn)

        # resource policy for api
        api_policy=iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=['execute-api:Invoke'],
                    principals=[iam.AnyPrincipal()],
                    resources=[f'arn:aws:execute-api:{region}:{acc}:*/prod/POST/*'],
                    effect=iam.Effect.ALLOW
                )
            ]
        )

        
        #creating API GTW
        api = apigateway.RestApi(self, "GTMAPI",
             endpoint_configuration=apigateway.EndpointConfiguration(
                 types=[apigateway.EndpointType.PRIVATE],
                 vpc_endpoints=apigw
             ),
             deploy_options=apigateway.StageOptions(
                logging_level=apigateway.MethodLoggingLevel.ERROR,
                data_trace_enabled=False,
                metrics_enabled=True,
                access_log_destination=apigateway.LogGroupLogDestination(access_logs),
            ),
            policy=api_policy
         )
        

        #creating cognito user pool
        user_pool = cognito.UserPool(self, "UserPool",advanced_security_mode=cognito.AdvancedSecurityMode.ENFORCED, 
            password_policy= cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            )
        )
        
        #Adding cognito user pool Auth to the api gateway
        auth = apigateway.CognitoUserPoolsAuthorizer(self, "requestAuthorizer",
        cognito_user_pools=[user_pool])

        # add mapping template to method
        kinesis_template = '{"StreamName" :"'+ stream_name +'"'+""",
                "PartitionKey" : $input.json('$.ga_session_id'),
                "Data" : "$util.base64Encode($input.json('$'))"}"""
        
        # adding method to the API GTW with responses and translation templates
        method=api.root.add_method("POST", apigateway.AwsIntegration(
            service='kinesis',
            action='PutRecord',
            options=apigateway.IntegrationOptions(
                credentials_role=api_role,
                request_templates={"application/json": kinesis_template},
                integration_responses=[apigateway.IntegrationResponse(status_code="200")],
                passthrough_behavior=apigateway.PassthroughBehavior.WHEN_NO_TEMPLATES,
                )
        ), 
            authorizer=auth,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        # add method response that will essentially be the integration response passed through
        method.add_method_response(status_code='200', response_models={'application/json': apigateway.Model.EMPTY_MODEL})
        method.grant_execute(api_role)

        #Adding request validator to API GTW
        api.add_request_validator('test-validator',
            request_validator_name='test-validator',
            validate_request_body=True,
            validate_request_parameters=True
        )
        # add usage plan and api-key
        plan = api.add_usage_plan("GTagStackUsagePlan", name="GTagStackUsagePlan")
        plan.add_api_stage(stage=api.deployment_stage)

        # add api key
        key = api.add_api_key("GTagStackApiKey", api_key_name="GTagStackApiKey",)
        plan.add_api_key(key)

        #Defining Kinesis data stream 
        stream=kds.Stream(self, 'KinesisDataStream', stream_name=stream_name)
        stream.grant(api_role, 'kinesis:PutRecords')
        stream.grant(api_role, 'kinesis:PutRecord')

        # S3 buckets needs to have unique names
        access_log_bucket_name=f"s3-access-log-{acc}-{region}"
        data_bucket_name=f"gtags3bucket-{acc}-{region}"

        #creating access log s3 bucket
        access_log_bucket=s3.Bucket(self, access_log_bucket_name, enforce_ssl=True,
                                    auto_delete_objects=True, removal_policy=RemovalPolicy.DESTROY)

        #data S3 bucket
        s3_bucket=s3.Bucket(self,"FirstBucket",bucket_name=data_bucket_name, enforce_ssl=True, 
                            server_access_logs_bucket=access_log_bucket,
                            auto_delete_objects=True, removal_policy=RemovalPolicy.DESTROY)

        #Creating Kinesis data firehose stream that writes to a S3 bucket
        firehose=KinesisStreamsToKinesisFirehoseToS3(self, 'gtag_stream_firehose_s3', 
                                                     existing_bucket_obj=s3_bucket,
                                                     existing_stream_obj=stream)
        
        