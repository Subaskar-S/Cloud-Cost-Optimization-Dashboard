"""
IAM Stack for Cost Optimization Dashboard
"""

from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_logs as logs
)
from constructs import Construct


class IAMStack(Stack):
    """Stack for IAM roles and policies used in cost optimization dashboard"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Lambda execution role for data collection
        self.data_collection_role = iam.Role(
            self, "DataCollectionRole",
            role_name="CostOptimization-DataCollection-Role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ]
        )

        # Add Cost Explorer permissions
        self.data_collection_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ce:GetCostAndUsage",
                    "ce:GetUsageReport",
                    "ce:GetReservationCoverage",
                    "ce:GetReservationPurchaseRecommendation",
                    "ce:GetReservationUtilization",
                    "ce:GetSavingsPlansUtilization",
                    "ce:GetSavingsPlansUtilizationDetails",
                    "ce:ListCostCategoryDefinitions",
                    "ce:GetRightsizingRecommendation"
                ],
                resources=["*"]
            )
        )

        # Add CloudWatch permissions
        self.data_collection_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudwatch:GetMetricStatistics",
                    "cloudwatch:GetMetricData",
                    "cloudwatch:ListMetrics"
                ],
                resources=["*"]
            )
        )

        # Add DynamoDB permissions (will be refined when tables are created)
        self.data_collection_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:PutItem",
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchWriteItem"
                ],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/cost-*"
                ]
            )
        )

        # Lambda execution role for data processing
        self.data_processing_role = iam.Role(
            self, "DataProcessingRole",
            role_name="CostOptimization-DataProcessing-Role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ]
        )

        # Add DynamoDB permissions for processing
        self.data_processing_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchGetItem",
                    "dynamodb:BatchWriteItem"
                ],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/cost-*",
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/cost-*/index/*"
                ]
            )
        )

        # Lambda execution role for alerting
        self.alerting_role = iam.Role(
            self, "AlertingRole",
            role_name="CostOptimization-Alerting-Role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ]
        )

        # Add DynamoDB read permissions for alerting
        self.alerting_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem"
                ],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/cost-*",
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/cost-*/index/*"
                ]
            )
        )

        # Add SNS permissions for alerting
        self.alerting_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sns:Publish"
                ],
                resources=[
                    f"arn:aws:sns:{self.region}:{self.account}:cost-*"
                ]
            )
        )

        # QuickSight service role
        self.quicksight_role = iam.Role(
            self, "QuickSightRole",
            role_name="CostOptimization-QuickSight-Role",
            assumed_by=iam.ServicePrincipal("quicksight.amazonaws.com")
        )

        # Add DynamoDB read permissions for QuickSight
        self.quicksight_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:DescribeTable"
                ],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/cost-*",
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/cost-*/index/*"
                ]
            )
        )

        # Add S3 permissions for QuickSight data export
        self.quicksight_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                resources=[
                    f"arn:aws:s3:::cost-optimization-dashboard-*",
                    f"arn:aws:s3:::cost-optimization-dashboard-*/*"
                ]
            )
        )

        # EventBridge role for triggering Lambda functions
        self.eventbridge_role = iam.Role(
            self, "EventBridgeRole",
            role_name="CostOptimization-EventBridge-Role",
            assumed_by=iam.ServicePrincipal("events.amazonaws.com")
        )

        # Add Lambda invoke permissions
        self.eventbridge_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "lambda:InvokeFunction"
                ],
                resources=[
                    f"arn:aws:lambda:{self.region}:{self.account}:function:cost-*"
                ]
            )
        )

        # Store role references for other stacks
        self.roles = {
            'data_collection': self.data_collection_role,
            'data_processing': self.data_processing_role,
            'alerting': self.alerting_role,
            'quicksight': self.quicksight_role,
            'eventbridge': self.eventbridge_role
        }
