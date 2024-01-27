import os
from aws_cdk import (
    Stack,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_s3 as s3,
    aws_logs as logs,
    aws_cognito as cognito,
    aws_kinesis as kds,
    RemovalPolicy,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_kinesisfirehose as kinesisfirehose
)
from aws_solutions_constructs.aws_kinesis_streams_kinesis_firehose_s3 import KinesisStreamsToKinesisFirehoseToS3
from constructs import Construct
from aws_cdk.aws_route53 import PrivateHostedZone, CnameRecord
from aws_cdk.aws_ecr_assets import Platform
DIRNAME = os.path.dirname(__file__)

class AWSAnalyticsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, 
                 apigw: [ec2.InterfaceVpcEndpoint], vpc: ec2.Vpc, load_balancer: elbv2.ApplicationLoadBalancer, 
                 cluster: ecs.ICluster, hosted_zone: PrivateHostedZone, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # flag to decide if api gateway or kinesis producer api is to be created
        data_capture_api_method = self.node.try_get_context("data_capture_api_method")
        producer_dns = self.node.try_get_context("producer_service_dns")

        # account and region
        acc = os.getenv('CDK_DEFAULT_ACCOUNT')
        region = os.getenv('CDK_DEFAULT_REGION')
        stream_name = "gtagStream"
        producer_svc_log_group = logs.LogGroup(self, "GTMProducerServiceLogGroup1LB",removal_policy=RemovalPolicy.DESTROY, log_group_name="GTMProducerServiceLogGroup1LB")
        producer_log_driver = ecs.AwsLogDriver(stream_prefix="GTMProducerLogDriver", log_group=producer_svc_log_group)

        #Defining Kinesis data stream 
        stream=kds.Stream(self, 'KinesisDataStream', stream_name=stream_name)

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
        
        # to address cdk nag AwsSolutions-KDF1
        del_stream_enc_conf_in_prop = kinesisfirehose.CfnDeliveryStream.DeliveryStreamEncryptionConfigurationInputProperty(
            key_type="AWS_OWNED_CMK"
        )
        
        # Creating Kinesis data firehose stream that writes to a S3 bucket
        # Cannot enable encryption for a delivery stream using kinesis streams as a source
        KinesisStreamsToKinesisFirehoseToS3(self, 'gtag_stream_firehose_s3', 
            existing_bucket_obj=s3_bucket,
            existing_stream_obj=stream,
            # kinesis_firehose_props=kinesisfirehose.CfnDeliveryStreamProps(
            #     delivery_stream_encryption_configuration_input=del_stream_enc_conf_in_prop)
        )
        
        # Depending up on the choice of ingestion method create resources
        if data_capture_api_method == "api_gateway":

            #creating Acess log group
            access_logs=logs.LogGroup(self, "ApiGatewayAccessLogs", log_group_name="GTMAnalyticsStackAPIGWLogs", removal_policy=RemovalPolicy.RETAIN)

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

            # add kinesis access
            stream.grant(api_role, 'kinesis:PutRecords')
            stream.grant(api_role, 'kinesis:PutRecord')

        else:
            # Producer service in the same cluster
            # cpu and memory min settings needed to avoid java heap error
            # may need to set DOCKER_DEFAULT_PLATFORM=linux/amd64 before starting deploy
            producer_task_definition = ecs.FargateTaskDefinition(self, "GTMproducerTaskDefinition1LB", 
                cpu=1024,
                memory_limit_mib=2048,
                runtime_platform=ecs.RuntimePlatform(cpu_architecture=ecs.CpuArchitecture.X86_64, operating_system_family=ecs.OperatingSystemFamily.LINUX)
            )

            producer_task_definition.add_container("GTMproducerContainer1LB",
                image=ecs.ContainerImage.from_asset("source/producer",
                    platform=Platform.LINUX_AMD64,
                    ),
                environment= {
                    'REGION': region,
                    'STREAM_NAME': stream_name,
                    'JAVA_TOOL_OPTIONS': '-XX:InitialHeapSize=1g -XX:MaxHeapSize=2g'
                },
                port_mappings=[ecs.PortMapping(container_port=8080, host_port=8080)],
                logging=producer_log_driver
            )
            gtm_producer_service = ecs.FargateService(self, "GTMproducerService1LB",
                service_name="GTMServerSideproducerService1LB",
                cluster=cluster,
                task_definition=producer_task_definition,
                desired_count=1,
            )

            load_balancer.listeners[0].add_targets(
                "GTMproducerServiceTargetGroup1LB",
                targets=[
                    gtm_producer_service.load_balancer_target(
                        container_name="GTMproducerContainer1LB",
                        container_port=8080
                    )
                ],
                conditions=[elbv2.ListenerCondition.host_headers([producer_dns])],
                priority=3,
                protocol=elbv2.ApplicationProtocol.HTTP,
                port=8080,
                health_check=elbv2.HealthCheck(path="/healthcheck", protocol=elbv2.Protocol.HTTP,port="8080")
            )

            gtm_producer_service.connections.allow_from(
                load_balancer.connections.security_groups[0],
                # lb_security_group,
                port_range=ec2.Port.tcp(8080),
                description="Allow inbound traffic from ELB to producer Service"
                )
            # -----------------------------------------------------------------------------------------------------------
            # defines the autoscaling configuration for producer service
            # -----------------------------------------------------------------------------------------------------------

            scalable_target = gtm_producer_service.auto_scale_task_count(
                max_capacity=10,
                min_capacity=1
            )

            scalable_target.scale_on_cpu_utilization("CpuScaling", 
                target_utilization_percent=70 
            )

            scalable_target.scale_on_memory_utilization("MemoryScaling",
                target_utilization_percent=70                
            )

            # Add cname to the existing hosted zone
            CnameRecord(self, "GTMPreviewRecord",
                record_name=producer_dns,
                zone=hosted_zone,
                domain_name=load_balancer.load_balancer_dns_name
            )

            # Connect the producer service to the kinesis stream
            stream.grant_read_write(gtm_producer_service.task_definition.task_role)
