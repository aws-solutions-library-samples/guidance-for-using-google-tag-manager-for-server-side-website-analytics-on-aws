import os

from aws_cdk import (
    Stack,
    aws_certificatemanager as acm,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_s3 as s3
)

from constructs import Construct
from jsii import interface

DIRNAME = os.path.dirname(__file__)

class ServerSideTaggerStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ssl_cert_arn = self.node.try_get_context("ssl_cert_arn")
        gtm_cloud_image = self.node.try_get_context("gtm_cloud_image")
        container_config = self.node.try_get_context("container_config")

        # -----------------------------------------------------------------------------------------------------------
        # defines a certificate from the ARN of a cert you have already created
        # -----------------------------------------------------------------------------------------------------------

        cert = acm.Certificate.from_certificate_arn(self, "GTMCert", ssl_cert_arn)

        # -----------------------------------------------------------------------------------------------------------
        # defines a VPC - this can be detailed to taste for the number of AZs and NAT Gateways desired
        # by default, we will create a VPC with three public subnets, three private subnets with a NAT GW in each AZ
        # -----------------------------------------------------------------------------------------------------------

        vpc = ec2.Vpc(self, "GTMVPC")

        # -----------------------------------------------------------------------------------------------------------
        # defines a VPC Interface Endpoint
        # This will allow the ECS container to send post requests to a Private API Gateway
        # -----------------------------------------------------------------------------------------------------------

        apigw_endpoint = vpc.add_interface_endpoint("APIGWInterfaceEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.APIGATEWAY
        )
        apigw_endpoints = []
        apigw_endpoints.append(apigw_endpoint)
        self.apigw_endpoints=apigw_endpoints
        # -----------------------------------------------------------------------------------------------------------
        # defines an ECS cluster
        # -----------------------------------------------------------------------------------------------------------

        cluster = ecs.Cluster(self, "GTMCluster", vpc=vpc)        

        # -----------------------------------------------------------------------------------------------------------
        # defines the preview google tag manager service
        # -----------------------------------------------------------------------------------------------------------

        gtm_preview_service = ecs_patterns.ApplicationLoadBalancedFargateService(self, "GTMPreviewService",
            cluster=cluster,
            memory_limit_mib=1024,
            cpu=256,
            desired_count=1,
            listener_port=443,
            certificate=cert,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry(gtm_cloud_image),
                environment= {
                    'PORT': '80',
                    'CONTAINER_CONFIG': container_config,
                    'RUN_AS_PREVIEW_SERVER': 'true',
                },
                container_port=80
            )
        )

        # -----------------------------------------------------------------------------------------------------------
        # defines the target group health check endpoint for the preview service
        # -----------------------------------------------------------------------------------------------------------

        gtm_preview_service.target_group.configure_health_check(
            path="/healthz"
        )
        
        # -----------------------------------------------------------------------------------------------------------
        # defines the primary google tag manager service
        # this service will have auto-scaling enabled by default
        # -----------------------------------------------------------------------------------------------------------


        gtm_service = ecs_patterns.ApplicationLoadBalancedFargateService(self, "GTMService",
            cluster=cluster,
            memory_limit_mib=1024,
            cpu=512,
            desired_count=3,
            listener_port=443,
            certificate=cert,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry(gtm_cloud_image),
                environment= {
                    'PORT': '80',
                    'CONTAINER_CONFIG': container_config,
                    'PREVIEW_SERVER_URL': 'https://'+gtm_preview_service.load_balancer.load_balancer_dns_name,
                },
                container_port=80
            ),

        )
        

        # -----------------------------------------------------------------------------------------------------------
        # defines the autoscaling configuration
        # -----------------------------------------------------------------------------------------------------------

        scalable_target = gtm_service.service.auto_scale_task_count(
            max_capacity=10,
            min_capacity=2
        )

        scalable_target.scale_on_cpu_utilization("CpuScaling", 
            target_utilization_percent=50 
        )

        scalable_target.scale_on_memory_utilization("MemoryScaling",
            target_utilization_percent=50                
        )
        
        # -----------------------------------------------------------------------------------------------------------
        # defines the target group health check endpoint
        # -----------------------------------------------------------------------------------------------------------

        gtm_service.target_group.configure_health_check(
            path="/healthz"
        )

