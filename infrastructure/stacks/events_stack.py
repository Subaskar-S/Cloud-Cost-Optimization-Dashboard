"""
Events Stack for Cost Optimization Dashboard
"""

import os
from aws_cdk import (
    Stack,
    aws_events as events,
    aws_events_targets as targets
)
from constructs import Construct


class EventsStack(Stack):
    """Stack for CloudWatch Events (EventBridge) rules for scheduled cost monitoring"""

    def __init__(self, scope: Construct, construct_id: str, 
                 lambda_functions: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.lambda_functions = lambda_functions

        # Get schedule configurations from environment variables
        cost_collection_schedule = os.environ.get('COST_COLLECTION_SCHEDULE', 'rate(1 hour)')
        analysis_schedule = os.environ.get('ANALYSIS_SCHEDULE', 'rate(6 hours)')
        alert_schedule = os.environ.get('ALERT_SCHEDULE', 'rate(15 minutes)')

        # Cost Data Collection Schedule
        self.cost_collection_rule = events.Rule(
            self, "CostCollectionRule",
            rule_name="cost-data-collection-schedule",
            description="Triggers cost data collection from AWS Cost Explorer",
            schedule=events.Schedule.expression(cost_collection_schedule),
            enabled=True
        )

        # Add Lambda target for cost collection
        self.cost_collection_rule.add_target(
            targets.LambdaFunction(
                lambda_functions['data_collection'],
                retry_attempts=2
            )
        )

        # Cost Data Processing Schedule
        self.cost_processing_rule = events.Rule(
            self, "CostProcessingRule",
            rule_name="cost-data-processing-schedule",
            description="Triggers cost data analysis and processing",
            schedule=events.Schedule.expression(analysis_schedule),
            enabled=True
        )

        # Add Lambda target for cost processing
        self.cost_processing_rule.add_target(
            targets.LambdaFunction(
                lambda_functions['data_processing'],
                retry_attempts=2
            )
        )

        # Cost Alerting Schedule
        self.cost_alerting_rule = events.Rule(
            self, "CostAlertingRule",
            rule_name="cost-alerting-schedule",
            description="Triggers cost threshold monitoring and alerting",
            schedule=events.Schedule.expression(alert_schedule),
            enabled=True
        )

        # Add Lambda target for alerting
        self.cost_alerting_rule.add_target(
            targets.LambdaFunction(
                lambda_functions['alerting'],
                retry_attempts=1
            )
        )

        # Daily Summary Report Schedule (9 AM UTC)
        self.daily_report_rule = events.Rule(
            self, "DailyReportRule",
            rule_name="daily-cost-report-schedule",
            description="Triggers daily cost summary report generation",
            schedule=events.Schedule.cron(
                minute="0",
                hour="9",
                day="*",
                month="*",
                year="*"
            ),
            enabled=True
        )

        # Add Lambda target for daily reports
        self.daily_report_rule.add_target(
            targets.LambdaFunction(
                lambda_functions['data_processing'],
                event=events.RuleTargetInput.from_object({
                    "report_type": "daily_summary"
                }),
                retry_attempts=2
            )
        )

        # Weekly Summary Report Schedule (Monday 9 AM UTC)
        self.weekly_report_rule = events.Rule(
            self, "WeeklyReportRule",
            rule_name="weekly-cost-report-schedule",
            description="Triggers weekly cost summary report generation",
            schedule=events.Schedule.cron(
                minute="0",
                hour="9",
                day="*",
                month="*",
                year="*",
                week_day="MON"
            ),
            enabled=True
        )

        # Add Lambda target for weekly reports
        self.weekly_report_rule.add_target(
            targets.LambdaFunction(
                lambda_functions['data_processing'],
                event=events.RuleTargetInput.from_object({
                    "report_type": "weekly_summary"
                }),
                retry_attempts=2
            )
        )

        # Monthly Summary Report Schedule (1st day of month, 9 AM UTC)
        self.monthly_report_rule = events.Rule(
            self, "MonthlyReportRule",
            rule_name="monthly-cost-report-schedule",
            description="Triggers monthly cost summary report generation",
            schedule=events.Schedule.cron(
                minute="0",
                hour="9",
                day="1",
                month="*",
                year="*"
            ),
            enabled=True
        )

        # Add Lambda target for monthly reports
        self.monthly_report_rule.add_target(
            targets.LambdaFunction(
                lambda_functions['data_processing'],
                event=events.RuleTargetInput.from_object({
                    "report_type": "monthly_summary"
                }),
                retry_attempts=2
            )
        )

        # Store rule references
        self.rules = {
            'cost_collection': self.cost_collection_rule,
            'cost_processing': self.cost_processing_rule,
            'cost_alerting': self.cost_alerting_rule,
            'daily_report': self.daily_report_rule,
            'weekly_report': self.weekly_report_rule,
            'monthly_report': self.monthly_report_rule
        }
