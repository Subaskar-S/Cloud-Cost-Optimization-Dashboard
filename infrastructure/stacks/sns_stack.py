"""
SNS Stack for Cost Optimization Dashboard
"""

import os
from aws_cdk import (
    Stack,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions
)
from constructs import Construct


class SNSStack(Stack):
    """Stack for SNS topics used in cost optimization dashboard"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Cost Alerts Topic - For threshold breaches and critical alerts
        self.cost_alerts_topic = sns.Topic(
            self, "CostAlertsTopic",
            topic_name="cost-alerts",
            display_name="Cost Optimization Alerts",
            fifo=False
        )

        # Cost Anomalies Topic - For unusual spending patterns
        self.cost_anomalies_topic = sns.Topic(
            self, "CostAnomaliesTopic",
            topic_name="cost-anomalies",
            display_name="Cost Anomaly Detection",
            fifo=False
        )

        # Cost Reports Topic - For scheduled reports and summaries
        self.cost_reports_topic = sns.Topic(
            self, "CostReportsTopic",
            topic_name="cost-reports",
            display_name="Cost Reports and Summaries",
            fifo=False
        )

        # Budget Alerts Topic - For budget-related notifications
        self.budget_alerts_topic = sns.Topic(
            self, "BudgetAlertsTopic",
            topic_name="budget-alerts",
            display_name="Budget Alerts",
            fifo=False
        )

        # Optimization Recommendations Topic - For cost optimization suggestions
        self.optimization_topic = sns.Topic(
            self, "OptimizationTopic",
            topic_name="cost-optimization",
            display_name="Cost Optimization Recommendations",
            fifo=False
        )

        # Add email subscriptions if configured
        notification_email = os.environ.get('NOTIFICATION_EMAIL')
        if notification_email:
            # Subscribe to critical alerts
            self.cost_alerts_topic.add_subscription(
                subscriptions.EmailSubscription(notification_email)
            )
            
            # Subscribe to anomaly alerts
            self.cost_anomalies_topic.add_subscription(
                subscriptions.EmailSubscription(notification_email)
            )
            
            # Subscribe to budget alerts
            self.budget_alerts_topic.add_subscription(
                subscriptions.EmailSubscription(notification_email)
            )

        # Add additional email subscriptions for reports (optional)
        reports_email = os.environ.get('REPORTS_EMAIL', notification_email)
        if reports_email:
            self.cost_reports_topic.add_subscription(
                subscriptions.EmailSubscription(reports_email)
            )
            
            self.optimization_topic.add_subscription(
                subscriptions.EmailSubscription(reports_email)
            )

        # Store topic references for other stacks
        self.topics = {
            'alerts': self.cost_alerts_topic,
            'anomalies': self.cost_anomalies_topic,
            'reports': self.cost_reports_topic,
            'budget': self.budget_alerts_topic,
            'optimization': self.optimization_topic
        }
