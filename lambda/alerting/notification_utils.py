"""
Notification utilities for cost alerting system
"""

import json
import requests
import boto3
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def send_slack_notification(webhook_url, alert):
    """
    Send alert notification to Slack
    """
    try:
        # Format Slack message
        color = get_alert_color(alert['severity'])
        
        slack_message = {
            "attachments": [
                {
                    "color": color,
                    "title": f"Cost Alert: {alert['service']}",
                    "title_link": "https://quicksight.aws.amazon.com/sn/dashboards/cost-optimization",
                    "fields": [
                        {
                            "title": "Service",
                            "value": alert['service'],
                            "short": True
                        },
                        {
                            "title": "Region",
                            "value": alert['region'],
                            "short": True
                        },
                        {
                            "title": "Current Cost",
                            "value": f"${float(alert['current_cost']):.2f}",
                            "short": True
                        },
                        {
                            "title": "Threshold",
                            "value": f"${float(alert['threshold']):.2f}",
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": alert['severity'].upper(),
                            "short": True
                        },
                        {
                            "title": "Alert Type",
                            "value": alert['alert_type'].replace('_', ' ').title(),
                            "short": True
                        }
                    ],
                    "text": alert['message'],
                    "footer": "AWS Cost Optimization Dashboard",
                    "ts": int(datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00')).timestamp())
                }
            ]
        }
        
        # Send to Slack
        response = requests.post(webhook_url, json=slack_message, timeout=10)
        response.raise_for_status()
        
        logger.info(f"Sent Slack notification for alert: {alert['alert_id']}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending Slack notification: {str(e)}")
        return False


def get_alert_color(severity):
    """
    Get color code for alert severity
    """
    colors = {
        'info': '#36a64f',      # Green
        'warning': '#ff9500',   # Orange
        'critical': '#ff0000'   # Red
    }
    return colors.get(severity, '#ff9500')


def format_email_notification(alert):
    """
    Format alert for email notification
    """
    html_template = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .alert-header {{ background-color: {get_email_bg_color(alert['severity'])}; 
                           color: white; padding: 15px; border-radius: 5px; }}
            .alert-content {{ padding: 20px; border: 1px solid #ddd; border-radius: 5px; margin-top: 10px; }}
            .alert-details {{ margin: 15px 0; }}
            .alert-details table {{ width: 100%; border-collapse: collapse; }}
            .alert-details th, .alert-details td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            .alert-details th {{ background-color: #f2f2f2; }}
            .actions {{ margin-top: 20px; padding: 15px; background-color: #f9f9f9; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="alert-header">
            <h2>🚨 Cost Alert: {alert['service']}</h2>
            <p>Severity: {alert['severity'].upper()}</p>
        </div>
        
        <div class="alert-content">
            <p><strong>Message:</strong> {alert['message']}</p>
            
            <div class="alert-details">
                <table>
                    <tr><th>Alert ID</th><td>{alert['alert_id']}</td></tr>
                    <tr><th>Alert Type</th><td>{alert['alert_type'].replace('_', ' ').title()}</td></tr>
                    <tr><th>Service</th><td>{alert['service']}</td></tr>
                    <tr><th>Region</th><td>{alert['region']}</td></tr>
                    <tr><th>Current Cost</th><td>${float(alert['current_cost']):.2f}</td></tr>
                    <tr><th>Threshold</th><td>${float(alert['threshold']):.2f}</td></tr>
                    <tr><th>Timestamp</th><td>{alert['timestamp']}</td></tr>
                </table>
            </div>
            
            <div class="actions">
                <h3>Recommended Actions:</h3>
                <ul>
                    <li>Review cost trends in the <a href="https://quicksight.aws.amazon.com/sn/dashboards/cost-optimization">Cost Dashboard</a></li>
                    <li>Investigate resource usage for {alert['service']} in {alert['region']}</li>
                    <li>Consider optimization opportunities</li>
                    <li>Acknowledge this alert once reviewed</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template


def get_email_bg_color(severity):
    """
    Get background color for email alerts
    """
    colors = {
        'info': '#17a2b8',      # Blue
        'warning': '#ffc107',   # Yellow
        'critical': '#dc3545'   # Red
    }
    return colors.get(severity, '#ffc107')


def create_alert_summary(alerts):
    """
    Create a summary of multiple alerts
    """
    if not alerts:
        return None
    
    summary = {
        'total_alerts': len(alerts),
        'by_severity': {},
        'by_service': {},
        'by_type': {},
        'highest_cost_alert': None,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    highest_cost = 0
    
    for alert in alerts:
        # Count by severity
        severity = alert['severity']
        summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
        
        # Count by service
        service = alert['service']
        summary['by_service'][service] = summary['by_service'].get(service, 0) + 1
        
        # Count by type
        alert_type = alert['alert_type']
        summary['by_type'][alert_type] = summary['by_type'].get(alert_type, 0) + 1
        
        # Track highest cost alert
        current_cost = float(alert['current_cost'])
        if current_cost > highest_cost:
            highest_cost = current_cost
            summary['highest_cost_alert'] = {
                'alert_id': alert['alert_id'],
                'service': alert['service'],
                'cost': current_cost,
                'message': alert['message']
            }
    
    return summary


def send_alert_digest(alerts, digest_type='daily'):
    """
    Send a digest of alerts (daily/weekly summary)
    """
    try:
        if not alerts:
            logger.info(f"No alerts to include in {digest_type} digest")
            return
        
        summary = create_alert_summary(alerts)
        
        # Create digest message
        digest_message = {
            'digest_type': digest_type,
            'summary': summary,
            'alerts': [
                {
                    'alert_id': alert['alert_id'],
                    'service': alert['service'],
                    'severity': alert['severity'],
                    'current_cost': float(alert['current_cost']),
                    'message': alert['message'],
                    'timestamp': alert['timestamp']
                }
                for alert in alerts
            ]
        }
        
        # Send digest notification
        # This would typically go to a different SNS topic for reports
        logger.info(f"Created {digest_type} alert digest with {len(alerts)} alerts")
        
        return digest_message
        
    except Exception as e:
        logger.error(f"Error creating alert digest: {str(e)}")
        return None


def escalate_alert(alert, escalation_level=1):
    """
    Escalate an alert to higher notification levels
    """
    try:
        escalation_config = {
            1: {
                'delay_minutes': 30,
                'recipients': ['manager@company.com'],
                'channels': ['email']
            },
            2: {
                'delay_minutes': 60,
                'recipients': ['director@company.com'],
                'channels': ['email', 'sms']
            },
            3: {
                'delay_minutes': 120,
                'recipients': ['cto@company.com'],
                'channels': ['email', 'sms', 'phone']
            }
        }
        
        config = escalation_config.get(escalation_level)
        if not config:
            logger.warning(f"No escalation config for level {escalation_level}")
            return False
        
        # Create escalated alert
        escalated_alert = alert.copy()
        escalated_alert['escalation_level'] = escalation_level
        escalated_alert['escalated_at'] = datetime.utcnow().isoformat()
        escalated_alert['escalation_recipients'] = config['recipients']
        
        logger.info(f"Escalated alert {alert['alert_id']} to level {escalation_level}")
        
        return escalated_alert
        
    except Exception as e:
        logger.error(f"Error escalating alert: {str(e)}")
        return None


def acknowledge_alert(alert_id, acknowledged_by):
    """
    Acknowledge an alert
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        alerts_table = dynamodb.Table('cost-alerts')
        
        # Update alert status
        response = alerts_table.update_item(
            Key={'alert_id': alert_id},
            UpdateExpression='SET acknowledged = :ack, acknowledged_by = :by, acknowledged_at = :at, #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':ack': True,
                ':by': acknowledged_by,
                ':at': datetime.utcnow().isoformat(),
                ':status': 'acknowledged'
            },
            ReturnValues='UPDATED_NEW'
        )
        
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return True
        
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
        return False


def resolve_alert(alert_id, resolved_by, resolution_notes=None):
    """
    Resolve an alert
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        alerts_table = dynamodb.Table('cost-alerts')
        
        update_expression = 'SET resolved = :res, resolved_at = :at, #status = :status'
        expression_values = {
            ':res': True,
            ':at': datetime.utcnow().isoformat(),
            ':status': 'resolved'
        }
        
        if resolved_by:
            update_expression += ', resolved_by = :by'
            expression_values[':by'] = resolved_by
        
        if resolution_notes:
            update_expression += ', resolution_notes = :notes'
            expression_values[':notes'] = resolution_notes
        
        response = alerts_table.update_item(
            Key={'alert_id': alert_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues=expression_values,
            ReturnValues='UPDATED_NEW'
        )
        
        logger.info(f"Alert {alert_id} resolved by {resolved_by}")
        return True
        
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {str(e)}")
        return False


def get_alert_metrics(days=7):
    """
    Get alert metrics for the specified number of days
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        alerts_table = dynamodb.Table('cost-alerts')
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Query alerts
        response = alerts_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('timestamp').between(
                start_date.isoformat(),
                end_date.isoformat()
            )
        )
        
        alerts = response.get('Items', [])
        
        # Calculate metrics
        metrics = {
            'total_alerts': len(alerts),
            'by_severity': {},
            'by_service': {},
            'by_status': {},
            'average_resolution_time': 0,
            'acknowledgment_rate': 0
        }
        
        acknowledged_count = 0
        resolution_times = []
        
        for alert in alerts:
            # Count by severity
            severity = alert.get('severity', 'unknown')
            metrics['by_severity'][severity] = metrics['by_severity'].get(severity, 0) + 1
            
            # Count by service
            service = alert.get('service', 'unknown')
            metrics['by_service'][service] = metrics['by_service'].get(service, 0) + 1
            
            # Count by status
            status = alert.get('status', 'unknown')
            metrics['by_status'][status] = metrics['by_status'].get(status, 0) + 1
            
            # Track acknowledgments
            if alert.get('acknowledged'):
                acknowledged_count += 1
            
            # Calculate resolution time
            if alert.get('resolved') and alert.get('resolved_at'):
                created_at = datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00'))
                resolved_at = datetime.fromisoformat(alert['resolved_at'].replace('Z', '+00:00'))
                resolution_time = (resolved_at - created_at).total_seconds() / 3600  # hours
                resolution_times.append(resolution_time)
        
        # Calculate rates and averages
        if len(alerts) > 0:
            metrics['acknowledgment_rate'] = round((acknowledged_count / len(alerts)) * 100, 1)
        
        if resolution_times:
            metrics['average_resolution_time'] = round(sum(resolution_times) / len(resolution_times), 1)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting alert metrics: {str(e)}")
        return None
