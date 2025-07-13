"""
AWS Cost Alerting Lambda Function
Monitors cost thresholds and sends alerts via SNS
"""

import json
import os
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from typing import Dict, List, Any
import uuid

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Get table names and topic ARNs from environment variables
COST_DATA_TABLE = os.environ['COST_DATA_TABLE']
COST_ANALYSIS_TABLE = os.environ['COST_ANALYSIS_TABLE']
CONFIG_TABLE = os.environ['CONFIG_TABLE']
ALERTS_TABLE = os.environ['ALERTS_TABLE']
ALERTS_TOPIC_ARN = os.environ['ALERTS_TOPIC_ARN']
ANOMALIES_TOPIC_ARN = os.environ['ANOMALIES_TOPIC_ARN']
BUDGET_TOPIC_ARN = os.environ['BUDGET_TOPIC_ARN']

# Initialize DynamoDB tables
cost_data_table = dynamodb.Table(COST_DATA_TABLE)
cost_analysis_table = dynamodb.Table(COST_ANALYSIS_TABLE)
config_table = dynamodb.Table(CONFIG_TABLE)
alerts_table = dynamodb.Table(ALERTS_TABLE)


def lambda_handler(event, context):
    """
    Main Lambda handler for cost alerting
    """
    try:
        logger.info("Starting cost alerting process")
        
        # Check if this is a test mode
        test_mode = event.get('test_mode', False)
        
        # Get alerting configuration
        config = get_alerting_config()
        
        # Check threshold alerts
        threshold_alerts = check_threshold_alerts(config, test_mode)
        
        # Check for cost anomalies
        anomaly_alerts = check_cost_anomalies(config, test_mode)
        
        # Check budget alerts
        budget_alerts = check_budget_alerts(config, test_mode)
        
        # Process and send alerts
        total_alerts = process_alerts(threshold_alerts + anomaly_alerts + budget_alerts)
        
        logger.info(f"Processed {total_alerts} alerts")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Cost alerting completed successfully',
                'threshold_alerts': len(threshold_alerts),
                'anomaly_alerts': len(anomaly_alerts),
                'budget_alerts': len(budget_alerts),
                'total_alerts': total_alerts,
                'timestamp': datetime.utcnow().isoformat()
            }, default=decimal_default)
        }
        
    except Exception as e:
        logger.error(f"Error in cost alerting: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }


def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def get_alerting_config():
    """
    Get alerting configuration from DynamoDB
    """
    try:
        response = config_table.get_item(
            Key={'config_type': 'thresholds'}
        )
        
        if 'Item' in response:
            return response['Item']
        else:
            # Return default configuration
            return {
                'cost_thresholds': {
                    'daily': {'warning': 100, 'critical': 200},
                    'weekly': {'warning': 500, 'critical': 1000},
                    'monthly': {'warning': 2000, 'critical': 4000}
                },
                'service_thresholds': {
                    'EC2': {'daily': 50, 'monthly': 1200},
                    'S3': {'daily': 20, 'monthly': 400}
                },
                'anomaly_detection': {
                    'enabled': True,
                    'sensitivity': 'medium'
                }
            }
    except Exception as e:
        logger.warning(f"Could not load alerting config, using defaults: {str(e)}")
        return {
            'cost_thresholds': {
                'daily': {'warning': 100, 'critical': 200}
            }
        }


def check_threshold_alerts(config, test_mode=False):
    """
    Check for cost threshold breaches
    """
    alerts = []
    
    try:
        # Get recent cost data
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=1)
        
        # Check daily thresholds
        daily_costs = get_daily_costs(start_date)
        daily_thresholds = config.get('cost_thresholds', {}).get('daily', {})
        
        total_daily_cost = sum(float(cost.get('cost_amount', 0)) for cost in daily_costs)
        
        # Check overall daily threshold
        for severity, threshold in daily_thresholds.items():
            if total_daily_cost > threshold:
                alert = create_alert(
                    alert_type='threshold_breach',
                    severity=severity,
                    service='Overall',
                    region='All',
                    current_cost=total_daily_cost,
                    threshold=threshold,
                    message=f"Daily costs ({total_daily_cost:.2f}) exceeded {severity} threshold ({threshold})",
                    test_mode=test_mode
                )
                alerts.append(alert)
        
        # Check service-specific thresholds
        service_thresholds = config.get('service_thresholds', {})
        service_costs = {}
        
        for record in daily_costs:
            service = record.get('service_name', 'Unknown')
            cost = float(record.get('cost_amount', 0))
            service_costs[service] = service_costs.get(service, 0) + cost
        
        for service, cost in service_costs.items():
            if service in service_thresholds:
                daily_threshold = service_thresholds[service].get('daily')
                if daily_threshold and cost > daily_threshold:
                    alert = create_alert(
                        alert_type='service_threshold_breach',
                        severity='warning',
                        service=service,
                        region='All',
                        current_cost=cost,
                        threshold=daily_threshold,
                        message=f"{service} daily costs ({cost:.2f}) exceeded threshold ({daily_threshold})",
                        test_mode=test_mode
                    )
                    alerts.append(alert)
        
        logger.info(f"Generated {len(alerts)} threshold alerts")
        return alerts
        
    except Exception as e:
        logger.error(f"Error checking threshold alerts: {str(e)}")
        return []


def check_cost_anomalies(config, test_mode=False):
    """
    Check for cost anomalies using statistical analysis
    """
    alerts = []
    
    try:
        anomaly_config = config.get('anomaly_detection', {})
        if not anomaly_config.get('enabled', True):
            return alerts
        
        # Get cost data for anomaly detection
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=14)  # 2 weeks of data
        
        cost_data = get_cost_data_range(start_date, end_date)
        
        # Detect anomalies by service
        anomalies = detect_service_anomalies(cost_data, anomaly_config.get('sensitivity', 'medium'))
        
        for anomaly in anomalies:
            alert = create_alert(
                alert_type='anomaly_detection',
                severity=anomaly['severity'],
                service=anomaly['service'],
                region=anomaly.get('region', 'All'),
                current_cost=float(anomaly['current_cost']),
                threshold=float(anomaly['expected_cost']),
                message=f"Cost anomaly detected for {anomaly['service']}: {anomaly['description']}",
                test_mode=test_mode
            )
            alerts.append(alert)
        
        logger.info(f"Generated {len(alerts)} anomaly alerts")
        return alerts
        
    except Exception as e:
        logger.error(f"Error checking cost anomalies: {str(e)}")
        return []


def check_budget_alerts(config, test_mode=False):
    """
    Check for budget threshold breaches
    """
    alerts = []
    
    try:
        # Get budget configuration
        budget_response = config_table.get_item(
            Key={'config_type': 'budgets'}
        )
        
        if 'Item' not in budget_response:
            return alerts
        
        budget_config = budget_response['Item']
        
        # Get current month's costs
        today = datetime.utcnow().date()
        first_day_month = today.replace(day=1)
        
        monthly_costs = get_cost_data_range(first_day_month, today)
        total_monthly_cost = sum(float(record.get('cost_amount', 0)) for record in monthly_costs)
        
        # Check overall budget
        overall_budget = budget_config.get('overall_budget', {})
        monthly_limit = overall_budget.get('monthly_limit')
        
        if monthly_limit:
            percentage_used = (total_monthly_cost / monthly_limit) * 100
            
            # Check various percentage thresholds
            if percentage_used >= 100:
                alert = create_alert(
                    alert_type='budget_exceeded',
                    severity='critical',
                    service='Overall',
                    region='All',
                    current_cost=total_monthly_cost,
                    threshold=monthly_limit,
                    message=f"Monthly budget exceeded: {total_monthly_cost:.2f} / {monthly_limit} ({percentage_used:.1f}%)",
                    test_mode=test_mode
                )
                alerts.append(alert)
            elif percentage_used >= 80:
                alert = create_alert(
                    alert_type='budget_warning',
                    severity='warning',
                    service='Overall',
                    region='All',
                    current_cost=total_monthly_cost,
                    threshold=monthly_limit * 0.8,
                    message=f"Monthly budget 80% reached: {total_monthly_cost:.2f} / {monthly_limit} ({percentage_used:.1f}%)",
                    test_mode=test_mode
                )
                alerts.append(alert)
        
        logger.info(f"Generated {len(alerts)} budget alerts")
        return alerts
        
    except Exception as e:
        logger.error(f"Error checking budget alerts: {str(e)}")
        return []


def get_daily_costs(date):
    """
    Get cost data for a specific date
    """
    try:
        date_str = date.strftime('%Y-%m-%d')
        
        response = cost_data_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('timestamp').begins_with(date_str)
        )
        
        return response.get('Items', [])
        
    except Exception as e:
        logger.error(f"Error retrieving daily costs for {date}: {str(e)}")
        return []


def get_cost_data_range(start_date, end_date):
    """
    Get cost data for a date range
    """
    try:
        response = cost_data_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('timestamp').between(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
        )
        
        cost_data = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = cost_data_table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('timestamp').between(
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                ),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            cost_data.extend(response.get('Items', []))
        
        return cost_data
        
    except Exception as e:
        logger.error(f"Error retrieving cost data range: {str(e)}")
        return []


def detect_service_anomalies(cost_data, sensitivity='medium'):
    """
    Detect cost anomalies by service using statistical methods
    """
    anomalies = []
    
    # Group by service and date
    service_daily_costs = {}
    
    for record in cost_data:
        service = record.get('service_name', 'Unknown')
        date = record['timestamp'][:10]
        cost = float(record.get('cost_amount', 0))
        
        if service not in service_daily_costs:
            service_daily_costs[service] = {}
        
        if date not in service_daily_costs[service]:
            service_daily_costs[service][date] = 0
        
        service_daily_costs[service][date] += cost
    
    # Set sensitivity thresholds
    sensitivity_thresholds = {
        'low': 3.0,
        'medium': 2.5,
        'high': 2.0
    }
    threshold = sensitivity_thresholds.get(sensitivity, 2.5)
    
    # Detect anomalies for each service
    for service, daily_costs in service_daily_costs.items():
        costs = list(daily_costs.values())
        
        if len(costs) < 7:  # Need at least a week of data
            continue
        
        # Calculate statistics
        from statistics import mean, stdev
        cost_mean = mean(costs)
        cost_std = stdev(costs) if len(costs) > 1 else 0
        
        # Check latest cost for anomaly
        latest_date = max(daily_costs.keys())
        latest_cost = daily_costs[latest_date]
        
        if cost_std > 0:
            z_score = abs(latest_cost - cost_mean) / cost_std
            
            if z_score > threshold:
                anomaly = {
                    'service': service,
                    'date': latest_date,
                    'current_cost': Decimal(str(round(latest_cost, 2))),
                    'expected_cost': Decimal(str(round(cost_mean, 2))),
                    'deviation': round(z_score, 2),
                    'severity': 'critical' if z_score > 3 else 'warning' if z_score > 2 else 'info',
                    'description': f"Cost {'spike' if latest_cost > cost_mean else 'drop'} detected (deviation: {z_score:.1f}σ)"
                }
                anomalies.append(anomaly)
    
    return anomalies


def create_alert(alert_type, severity, service, region, current_cost, threshold, message, test_mode=False):
    """
    Create an alert record
    """
    timestamp = datetime.utcnow()
    alert_id = f"{alert_type}_{service.lower().replace(' ', '_')}_{region}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

    alert = {
        'alert_id': alert_id,
        'timestamp': timestamp.isoformat(),
        'alert_type': alert_type,
        'severity': severity,
        'service': service,
        'region': region,
        'current_cost': Decimal(str(round(current_cost, 2))),
        'threshold': Decimal(str(round(threshold, 2))),
        'message': message,
        'status': 'active',
        'acknowledged': False,
        'acknowledged_by': None,
        'acknowledged_at': None,
        'resolved': False,
        'resolved_at': None,
        'notification_sent': False,
        'notification_channels': [],
        'test_mode': test_mode,
        'ttl': int((datetime.utcnow() + timedelta(days=30)).timestamp())
    }

    return alert


def process_alerts(alerts):
    """
    Process and send alerts
    """
    if not alerts:
        return 0

    processed_count = 0

    for alert in alerts:
        try:
            # Check if similar alert already exists
            if not is_duplicate_alert(alert):
                # Store alert in DynamoDB
                store_alert(alert)

                # Send notification
                send_alert_notification(alert)

                processed_count += 1
                logger.info(f"Processed alert: {alert['alert_id']}")
            else:
                logger.info(f"Skipped duplicate alert: {alert['alert_id']}")

        except Exception as e:
            logger.error(f"Error processing alert {alert.get('alert_id', 'unknown')}: {str(e)}")

    return processed_count


def is_duplicate_alert(alert):
    """
    Check if a similar alert already exists
    """
    try:
        # Look for recent alerts of the same type for the same service
        recent_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        response = alerts_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('alert_type').eq(alert['alert_type']) &
                           boto3.dynamodb.conditions.Attr('service').eq(alert['service']) &
                           boto3.dynamodb.conditions.Attr('region').eq(alert['region']) &
                           boto3.dynamodb.conditions.Attr('timestamp').gt(recent_time) &
                           boto3.dynamodb.conditions.Attr('status').eq('active')
        )

        return len(response.get('Items', [])) > 0

    except Exception as e:
        logger.error(f"Error checking for duplicate alerts: {str(e)}")
        return False


def store_alert(alert):
    """
    Store alert in DynamoDB
    """
    try:
        alerts_table.put_item(Item=alert)
        logger.info(f"Stored alert: {alert['alert_id']}")

    except Exception as e:
        logger.error(f"Error storing alert: {str(e)}")
        raise


def send_alert_notification(alert):
    """
    Send alert notification via SNS
    """
    try:
        # Determine the appropriate SNS topic
        topic_arn = get_topic_for_alert(alert)

        if not topic_arn:
            logger.warning(f"No topic configured for alert type: {alert['alert_type']}")
            return

        # Format the message
        message = format_alert_message(alert)
        subject = format_alert_subject(alert)

        # Send to SNS
        response = sns.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=json.dumps(message, default=decimal_default)
        )

        # Update alert to mark notification as sent
        alerts_table.update_item(
            Key={
                'alert_id': alert['alert_id'],
                'timestamp': alert['timestamp']
            },
            UpdateExpression='SET notification_sent = :sent, notification_channels = :channels',
            ExpressionAttributeValues={
                ':sent': True,
                ':channels': ['email', 'slack']
            }
        )

        logger.info(f"Sent notification for alert: {alert['alert_id']}")

    except Exception as e:
        logger.error(f"Error sending alert notification: {str(e)}")


def get_topic_for_alert(alert):
    """
    Get the appropriate SNS topic for an alert
    """
    alert_type = alert['alert_type']

    if alert_type in ['threshold_breach', 'service_threshold_breach']:
        return ALERTS_TOPIC_ARN
    elif alert_type == 'anomaly_detection':
        return ANOMALIES_TOPIC_ARN
    elif alert_type in ['budget_exceeded', 'budget_warning']:
        return BUDGET_TOPIC_ARN
    else:
        return ALERTS_TOPIC_ARN  # Default


def format_alert_message(alert):
    """
    Format alert message for notification
    """
    return {
        'alert_id': alert['alert_id'],
        'alert_type': alert['alert_type'],
        'severity': alert['severity'],
        'service': alert['service'],
        'region': alert['region'],
        'current_cost': float(alert['current_cost']),
        'threshold': float(alert['threshold']),
        'message': alert['message'],
        'timestamp': alert['timestamp'],
        'dashboard_link': f"https://quicksight.aws.amazon.com/sn/dashboards/cost-optimization",
        'actions': {
            'acknowledge': f"aws dynamodb update-item --table-name {ALERTS_TABLE} --key '{\"alert_id\": {\"S\": \"{alert['alert_id']}\"}}'",
            'investigate': f"Check cost trends for {alert['service']} in {alert['region']}"
        }
    }


def format_alert_subject(alert):
    """
    Format alert subject line
    """
    severity_emoji = {
        'info': 'ℹ️',
        'warning': '⚠️',
        'critical': '🚨'
    }

    emoji = severity_emoji.get(alert['severity'], '⚠️')

    return f"{emoji} Cost Alert: {alert['service']} - {alert['severity'].upper()}"
