#!/usr/bin/env python3
"""
AWS CDK App for Cost Optimization Dashboard
"""

import os
from aws_cdk import App, Environment
from stacks.dynamodb_stack import DynamoDBStack
from stacks.lambda_stack import LambdaStack
from stacks.events_stack import EventsStack
from stacks.sns_stack import SNSStack
from stacks.iam_stack import IAMStack

# Get environment variables
account = os.environ.get('CDK_DEFAULT_ACCOUNT', os.environ.get('AWS_ACCOUNT_ID'))
region = os.environ.get('CDK_DEFAULT_REGION', os.environ.get('AWS_REGION', 'us-east-1'))

app = App()

# Define environment
env = Environment(account=account, region=region)

# Stack naming prefix
stack_prefix = "CostOptimization"

# Create IAM stack first (other stacks depend on it)
iam_stack = IAMStack(
    app, 
    f"{stack_prefix}-IAM",
    env=env,
    description="IAM roles and policies for Cost Optimization Dashboard"
)

# Create DynamoDB stack
dynamodb_stack = DynamoDBStack(
    app, 
    f"{stack_prefix}-DynamoDB",
    env=env,
    description="DynamoDB tables for cost data storage"
)

# Create SNS stack
sns_stack = SNSStack(
    app, 
    f"{stack_prefix}-SNS",
    env=env,
    description="SNS topics for cost alerts and notifications"
)

# Create Lambda stack (depends on IAM, DynamoDB, and SNS)
lambda_stack = LambdaStack(
    app, 
    f"{stack_prefix}-Lambda",
    iam_roles=iam_stack.roles,
    dynamodb_tables=dynamodb_stack.tables,
    sns_topics=sns_stack.topics,
    env=env,
    description="Lambda functions for cost data processing"
)

# Create Events stack (depends on Lambda)
events_stack = EventsStack(
    app, 
    f"{stack_prefix}-Events",
    lambda_functions=lambda_stack.functions,
    env=env,
    description="CloudWatch Events for scheduled cost monitoring"
)

# Add dependencies
lambda_stack.add_dependency(iam_stack)
lambda_stack.add_dependency(dynamodb_stack)
lambda_stack.add_dependency(sns_stack)
events_stack.add_dependency(lambda_stack)

# Add tags to all stacks
for stack in [iam_stack, dynamodb_stack, sns_stack, lambda_stack, events_stack]:
    stack.tags.set_tag("Project", "CostOptimizationDashboard")
    stack.tags.set_tag("Environment", os.environ.get("ENVIRONMENT", "production"))
    stack.tags.set_tag("Owner", "DevOps")
    stack.tags.set_tag("CostCenter", "Infrastructure")

app.synth()
