"""
Lambda Stack for Cost Optimization Dashboard
"""

import os
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_lambda_python_alpha as python_lambda,
    Duration
)
from constructs import Construct


class LambdaStack(Stack):
    """Stack for Lambda functions used in cost optimization dashboard"""

    def __init__(self, scope: Construct, construct_id: str, 
                 iam_roles: dict, dynamodb_tables: dict, sns_topics: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.iam_roles = iam_roles
        self.dynamodb_tables = dynamodb_tables
        self.sns_topics = sns_topics

        # Common environment variables for all Lambda functions
        common_env = {
            'COST_DATA_TABLE': dynamodb_tables['cost_data'].table_name,
            'COST_ANALYSIS_TABLE': dynamodb_tables['cost_analysis'].table_name,
            'CONFIG_TABLE': dynamodb_tables['config'].table_name,
            'ALERTS_TABLE': dynamodb_tables['alerts'].table_name,
            'RECOMMENDATIONS_TABLE': dynamodb_tables['recommendations'].table_name,
            'ALERTS_TOPIC_ARN': sns_topics['alerts'].topic_arn,
            'ANOMALIES_TOPIC_ARN': sns_topics['anomalies'].topic_arn,
            'REPORTS_TOPIC_ARN': sns_topics['reports'].topic_arn,
            'BUDGET_TOPIC_ARN': sns_topics['budget'].topic_arn,
            'OPTIMIZATION_TOPIC_ARN': sns_topics['optimization'].topic_arn,
            'AWS_REGION': self.region
        }

        # Data Collection Lambda Function
        self.data_collection_function = python_lambda.PythonFunction(
            self, "DataCollectionFunction",
            function_name="cost-data-collection",
            entry="../lambda/data_collection",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="handler.lambda_handler",
            timeout=Duration.minutes(5),
            memory_size=512,
            role=iam_roles['data_collection'],
            environment=common_env,
            description="Collects cost data from AWS Cost Explorer and CloudWatch"
        )

        # Data Processing Lambda Function
        self.data_processing_function = python_lambda.PythonFunction(
            self, "DataProcessingFunction",
            function_name="cost-data-processing",
            entry="../lambda/data_processing",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="handler.lambda_handler",
            timeout=Duration.minutes(10),
            memory_size=1024,
            role=iam_roles['data_processing'],
            environment=common_env,
            description="Processes and analyzes cost data for trends and insights"
        )

        # Alerting Lambda Function
        self.alerting_function = python_lambda.PythonFunction(
            self, "AlertingFunction",
            function_name="cost-alerting",
            entry="../lambda/alerting",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="handler.lambda_handler",
            timeout=Duration.minutes(2),
            memory_size=256,
            role=iam_roles['alerting'],
            environment=common_env,
            description="Monitors cost thresholds and sends alerts"
        )

        # Grant DynamoDB permissions to Lambda functions
        for table in dynamodb_tables.values():
            table.grant_read_write_data(self.data_collection_function)
            table.grant_read_write_data(self.data_processing_function)
            table.grant_read_data(self.alerting_function)

        # Grant additional write permissions to alerting function for alerts table
        dynamodb_tables['alerts'].grant_write_data(self.alerting_function)

        # Grant SNS publish permissions to alerting function
        for topic in sns_topics.values():
            topic.grant_publish(self.alerting_function)

        # Store function references for other stacks
        self.functions = {
            'data_collection': self.data_collection_function,
            'data_processing': self.data_processing_function,
            'alerting': self.alerting_function
        }
