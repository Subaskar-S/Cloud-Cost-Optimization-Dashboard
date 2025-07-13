"""
DynamoDB Stack for Cost Optimization Dashboard
"""

from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    Duration
)
from constructs import Construct


class DynamoDBStack(Stack):
    """Stack for DynamoDB tables used in cost optimization dashboard"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Cost Data Table - Main table for storing cost and usage data
        self.cost_data_table = dynamodb.Table(
            self, "CostDataTable",
            table_name="cost-data",
            partition_key=dynamodb.Attribute(
                name="service_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.ON_DEMAND,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
            time_to_live_attribute="ttl",
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
        )

        # Global Secondary Index for region-based queries
        self.cost_data_table.add_global_secondary_index(
            index_name="region-timestamp-index",
            partition_key=dynamodb.Attribute(
                name="region",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Global Secondary Index for tag-based queries
        self.cost_data_table.add_global_secondary_index(
            index_name="tag-timestamp-index",
            partition_key=dynamodb.Attribute(
                name="tag_key",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Cost Analysis Table - Stores processed analysis results
        self.cost_analysis_table = dynamodb.Table(
            self, "CostAnalysisTable",
            table_name="cost-analysis",
            partition_key=dynamodb.Attribute(
                name="analysis_type",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="period",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.ON_DEMAND,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
            time_to_live_attribute="ttl"
        )

        # Global Secondary Index for time-based analysis queries
        self.cost_analysis_table.add_global_secondary_index(
            index_name="created-at-index",
            partition_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Configuration Table - Stores thresholds, budgets, and settings
        self.config_table = dynamodb.Table(
            self, "ConfigTable",
            table_name="cost-config",
            partition_key=dynamodb.Attribute(
                name="config_type",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.ON_DEMAND,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True
        )

        # Alerts Table - Stores alert history and status
        self.alerts_table = dynamodb.Table(
            self, "AlertsTable",
            table_name="cost-alerts",
            partition_key=dynamodb.Attribute(
                name="alert_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.ON_DEMAND,
            removal_policy=RemovalPolicy.RETAIN,
            time_to_live_attribute="ttl"
        )

        # Global Secondary Index for alert status queries
        self.alerts_table.add_global_secondary_index(
            index_name="status-timestamp-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Optimization Recommendations Table
        self.recommendations_table = dynamodb.Table(
            self, "RecommendationsTable",
            table_name="cost-recommendations",
            partition_key=dynamodb.Attribute(
                name="resource_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="recommendation_type",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.ON_DEMAND,
            removal_policy=RemovalPolicy.RETAIN,
            time_to_live_attribute="ttl"
        )

        # Global Secondary Index for recommendation priority queries
        self.recommendations_table.add_global_secondary_index(
            index_name="priority-savings-index",
            partition_key=dynamodb.Attribute(
                name="priority",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="estimated_savings",
                type=dynamodb.AttributeType.NUMBER
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Store table references for other stacks
        self.tables = {
            'cost_data': self.cost_data_table,
            'cost_analysis': self.cost_analysis_table,
            'config': self.config_table,
            'alerts': self.alerts_table,
            'recommendations': self.recommendations_table
        }
