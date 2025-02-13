# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Licensed under the Apache License Version 2.0 (the "License"). You may not use this file except
# in compliance with the License. A copy of the License is located at http://www.apache.org/licenses/
# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the
# specific language governing permissions and limitations under the License.
import os
from aws_cdk import (
    Stack,
    aws_certificatemanager as acm,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    RemovalPolicy,
    aws_logs as logs,
)
from aws_cdk.aws_elasticloadbalancingv2 import ListenerCondition, Protocol, HealthCheck, ApplicationProtocol
from aws_cdk.aws_route53 import PrivateHostedZone, CnameRecord
from constructs import Construct

DIRNAME = os.path.dirname(__file__)

class ServerSideTaggerStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ssl_cert_arn = self.node.try_get_context("ssl_cert_arn")
        gtm_cloud_image = self.node.try_get_context("gtm_cloud_image")
        container_config = self.node.try_get_context("container_config")
        # added below to address certifcate validation error in the logs
        # using the alb default dns causes certifcate validation error as the SSL may not have that entry
        preview_dns = self.node.try_get_context("preview_server_dns")
        # adding below to include in target groups
        primary_dns = self.node.try_get_context("primary_server_dns")
        root_dns = self.node.try_get_context("root_dns")
        # -----------------------------------------------------------------------------------------------------------
        # defines a certificate from the ARN of a cert you have already created
        # -----------------------------------------------------------------------------------------------------------

        cert = acm.Certificate.from_certificate_arn(self, "GTMCert", ssl_cert_arn)

        # -----------------------------------------------------------------------------------------------------------
        # defines a VPC - this can be detailed to taste for the number of AZs and NAT Gateways desired
        # by default, we will create a VPC with three public subnets, three private subnets with a NAT GW in each AZ
        # -----------------------------------------------------------------------------------------------------------

        vpc = ec2.Vpc(self, "GTMVPC", vpc_name="GTMServerSideVPC")
        self.vpc = vpc

        # -----------------------------------------------------------------------------------------------------------
        # defines an ECS cluster
        # -----------------------------------------------------------------------------------------------------------

        cluster = ecs.Cluster(self, "GTMCluster", vpc=vpc, cluster_name="GTMServerSideCluster")        
        self.ecs_cluster = cluster

        # -----------------------------------------------------------------------------------------------------------
        # defines the primary google tag manager service
        # Creating this first to have the default rule to be preview and priority 1 rule is primary
        # this is to avoid rule evaluations on the majority of traffic
        # -----------------------------------------------------------------------------------------------------------

        primary_svc_log_group = logs.LogGroup(self, "GTMPrimaryServiceLogGroup",removal_policy=RemovalPolicy.DESTROY, log_group_name="GTMPrimaryServiceLogGroup")
        primary_log_driver = ecs.AwsLogDriver(stream_prefix="GTMServerSide", log_group=primary_svc_log_group)
        preview_svc_log_group = logs.LogGroup(self, "GTMPreviewServiceLogGroup",removal_policy=RemovalPolicy.DESTROY, log_group_name="GTMPreviewServiceLogGroup")
        preview_log_driver = ecs.AwsLogDriver(stream_prefix="GTMServerSide", log_group=preview_svc_log_group)

        gtm_preview_service = ecs_patterns.ApplicationLoadBalancedFargateService(self, "GTMService",
            cluster=cluster,
            memory_limit_mib=1024,
            cpu=512,
            desired_count=1,
            listener_port=443,
            certificate=cert,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry(gtm_cloud_image),
                environment= {
                    'PORT': '80',
                    'CONTAINER_CONFIG': container_config,
                    'RUN_AS_PREVIEW_SERVER': 'true',
                    'CONTAINER_REFRESH_SECONDS': '86400',
                },
                container_port=80,
                log_driver=preview_log_driver,
            ),
            service_name="GTMServerSidePreviewService",
            load_balancer_name="GTMServerSideLoadBalancer",
        )

        # -----------------------------------------------------------------------------------------------------------
        # defines the target group health check endpoint for the preview service
        # -----------------------------------------------------------------------------------------------------------

        gtm_preview_service.target_group.configure_health_check(
            path="/healthz"
        )
        self.load_balancer = gtm_preview_service.load_balancer

        # -----------------------------------------------------------------------------------------------------------
        # defines the primary google tag manager service
        # this service will have auto-scaling enabled by default
        # -----------------------------------------------------------------------------------------------------------
        
        primary_task_definition = ecs.FargateTaskDefinition(self, "GTMPrimaryTaskDefinition", 
            cpu=512,
            memory_limit_mib=1024
        )

        primary_task_definition.add_container("GTMPrimaryContainer",
            image=ecs.ContainerImage.from_registry(gtm_cloud_image),
            environment= {
                'PORT': '80',
                'CONTAINER_CONFIG': container_config,
                'PREVIEW_SERVER_URL': f'https://{preview_dns}',
                'CONTAINER_REFRESH_SECONDS': '86400',
            },
            port_mappings=[ecs.PortMapping(container_port=80, host_port=80)],
            logging=primary_log_driver
        )
        gtm_service = ecs.FargateService(self, "GTMPrimaryService",
            service_name="GTMServerSidePrimaryService",
            cluster=cluster,
            task_definition=primary_task_definition,
            desired_count=3,
        )

        gtm_preview_service.load_balancer.listeners[0].add_targets(
            "GTMPrimaryServiceTargetGroup",
            targets=[
                gtm_service.load_balancer_target(
                    container_name="GTMPrimaryContainer",
                    container_port=80
                )
            ],
            conditions=[ListenerCondition.host_headers([primary_dns])],
            priority=1,
            protocol=ApplicationProtocol.HTTP,
            health_check=HealthCheck(path="/healthz", protocol=Protocol.HTTP)
        )

        gtm_service.connections.allow_from(
            gtm_preview_service.load_balancer.connections.security_groups[0],
            # lb_security_group,
            port_range=ec2.Port.tcp(80),
            description="Allow inbound traffic from ELB to Primary Service"
            )
        # -----------------------------------------------------------------------------------------------------------
        # defines the autoscaling configuration for primary service
        # -----------------------------------------------------------------------------------------------------------

        scalable_target = gtm_service.auto_scale_task_count(
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
        # defines the hosted zone for internal DNS resolution from primary service to preview service and SSL handling
        # -----------------------------------------------------------------------------------------------------------
        domain_zone=PrivateHostedZone(self, "GTMHostedZone", zone_name=root_dns,vpc=vpc)
        self.hosted_zone=domain_zone
        
        CnameRecord(self, "GTMPreviewRecord",
            record_name=preview_dns,
            zone=domain_zone,
            domain_name=gtm_preview_service.load_balancer.load_balancer_dns_name
        )
