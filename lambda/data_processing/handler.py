"""
AWS Cost Data Processing and Analysis Lambda Function
Processes cost data to generate insights, trends, and optimization recommendations
"""

import json
import os
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from typing import Dict, List, Any
from statistics import mean, median
import math

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
RECOMMENDATIONS_TABLE = os.environ['RECOMMENDATIONS_TABLE']
REPORTS_TOPIC_ARN = os.environ['REPORTS_TOPIC_ARN']

# Initialize DynamoDB tables
cost_data_table = dynamodb.Table(COST_DATA_TABLE)
cost_analysis_table = dynamodb.Table(COST_ANALYSIS_TABLE)
config_table = dynamodb.Table(CONFIG_TABLE)
recommendations_table = dynamodb.Table(RECOMMENDATIONS_TABLE)


def lambda_handler(event, context):
    """
    Main Lambda handler for cost data processing and analysis
    """
    try:
        logger.info("Starting cost data processing and analysis")
        
        # Determine the type of processing based on event
        report_type = event.get('report_type', 'analysis')
        
        if report_type == 'daily_summary':
            result = generate_daily_summary()
        elif report_type == 'weekly_summary':
            result = generate_weekly_summary()
        elif report_type == 'monthly_summary':
            result = generate_monthly_summary()
        else:
            # Default analysis processing
            result = process_cost_analysis()
        
        logger.info(f"Successfully completed {report_type} processing")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'{report_type} processing completed successfully',
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            }, default=decimal_default)
        }
        
    except Exception as e:
        logger.error(f"Error in cost data processing: {str(e)}")
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


def process_cost_analysis():
    """
    Main cost analysis processing function
    """
    # Get cost data for analysis
    cost_data = get_recent_cost_data(days=30)
    
    # Perform various analyses
    daily_analysis = analyze_daily_costs(cost_data)
    trend_analysis = analyze_cost_trends(cost_data)
    service_analysis = analyze_service_costs(cost_data)
    regional_analysis = analyze_regional_costs(cost_data)
    
    # Generate optimization recommendations
    recommendations = generate_optimization_recommendations(cost_data)
    
    # Store analysis results
    store_analysis_results('trend_analysis', {
        'daily_analysis': daily_analysis,
        'trend_analysis': trend_analysis,
        'service_analysis': service_analysis,
        'regional_analysis': regional_analysis,
        'recommendations': recommendations
    })
    
    return {
        'daily_analysis': daily_analysis,
        'trend_analysis': trend_analysis,
        'service_analysis': service_analysis,
        'regional_analysis': regional_analysis,
        'recommendations_generated': len(recommendations)
    }


def get_recent_cost_data(days=30):
    """
    Retrieve recent cost data for analysis
    """
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    cost_data = []
    
    try:
        # Scan the table for recent data (in production, use more efficient queries)
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
        
        logger.info(f"Retrieved {len(cost_data)} cost records for analysis")
        return cost_data
        
    except Exception as e:
        logger.error(f"Error retrieving cost data: {str(e)}")
        return []


def analyze_daily_costs(cost_data):
    """
    Analyze daily cost patterns
    """
    daily_costs = {}
    
    for record in cost_data:
        date = record['timestamp'][:10]  # Extract date part
        cost = float(record.get('cost_amount', 0))
        
        if date not in daily_costs:
            daily_costs[date] = 0
        daily_costs[date] += cost
    
    # Calculate statistics
    costs = list(daily_costs.values())
    if not costs:
        return {}
    
    return {
        'total_days': len(daily_costs),
        'average_daily_cost': Decimal(str(round(mean(costs), 2))),
        'median_daily_cost': Decimal(str(round(median(costs), 2))),
        'min_daily_cost': Decimal(str(round(min(costs), 2))),
        'max_daily_cost': Decimal(str(round(max(costs), 2))),
        'total_cost': Decimal(str(round(sum(costs), 2))),
        'daily_breakdown': {date: Decimal(str(round(cost, 2))) for date, cost in daily_costs.items()}
    }


def analyze_cost_trends(cost_data):
    """
    Analyze cost trends and patterns
    """
    # Group data by date
    daily_costs = {}
    for record in cost_data:
        date = record['timestamp'][:10]
        cost = float(record.get('cost_amount', 0))
        
        if date not in daily_costs:
            daily_costs[date] = 0
        daily_costs[date] += cost
    
    # Sort by date
    sorted_dates = sorted(daily_costs.keys())
    if len(sorted_dates) < 2:
        return {}
    
    # Calculate trend
    costs = [daily_costs[date] for date in sorted_dates]
    
    # Simple linear trend calculation
    n = len(costs)
    x_mean = (n - 1) / 2
    y_mean = mean(costs)
    
    numerator = sum((i - x_mean) * (costs[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    
    slope = numerator / denominator if denominator != 0 else 0
    
    # Calculate percentage change
    if len(costs) >= 7:
        recent_avg = mean(costs[-7:])  # Last 7 days
        previous_avg = mean(costs[-14:-7]) if len(costs) >= 14 else mean(costs[:-7])
        percent_change = ((recent_avg - previous_avg) / previous_avg * 100) if previous_avg > 0 else 0
    else:
        percent_change = 0
    
    return {
        'trend_direction': 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable',
        'daily_change_rate': Decimal(str(round(slope, 4))),
        'percent_change_week': Decimal(str(round(percent_change, 2))),
        'volatility': Decimal(str(round(math.sqrt(sum((c - y_mean) ** 2 for c in costs) / n), 2))),
        'trend_strength': min(abs(slope) * 10, 100)  # Normalized trend strength
    }


def analyze_service_costs(cost_data):
    """
    Analyze costs by AWS service
    """
    service_costs = {}
    
    for record in cost_data:
        service = record.get('service_name', 'Unknown')
        cost = float(record.get('cost_amount', 0))
        
        if service not in service_costs:
            service_costs[service] = {
                'total_cost': 0,
                'record_count': 0,
                'regions': set()
            }
        
        service_costs[service]['total_cost'] += cost
        service_costs[service]['record_count'] += 1
        service_costs[service]['regions'].add(record.get('region', 'unknown'))
    
    # Convert to serializable format and calculate percentages
    total_cost = sum(data['total_cost'] for data in service_costs.values())
    
    result = {}
    for service, data in service_costs.items():
        result[service] = {
            'total_cost': Decimal(str(round(data['total_cost'], 2))),
            'percentage': Decimal(str(round((data['total_cost'] / total_cost * 100) if total_cost > 0 else 0, 2))),
            'average_cost': Decimal(str(round(data['total_cost'] / data['record_count'], 2))),
            'region_count': len(data['regions'])
        }
    
    # Sort by total cost
    sorted_services = sorted(result.items(), key=lambda x: x[1]['total_cost'], reverse=True)
    
    return {
        'service_breakdown': dict(sorted_services),
        'top_service': sorted_services[0][0] if sorted_services else None,
        'service_count': len(service_costs),
        'total_cost': Decimal(str(round(total_cost, 2)))
    }


def analyze_regional_costs(cost_data):
    """
    Analyze costs by AWS region
    """
    regional_costs = {}
    
    for record in cost_data:
        region = record.get('region', 'unknown')
        cost = float(record.get('cost_amount', 0))
        
        if region not in regional_costs:
            regional_costs[region] = {
                'total_cost': 0,
                'services': set()
            }
        
        regional_costs[region]['total_cost'] += cost
        regional_costs[region]['services'].add(record.get('service_name', 'Unknown'))
    
    # Convert to serializable format
    total_cost = sum(data['total_cost'] for data in regional_costs.values())
    
    result = {}
    for region, data in regional_costs.items():
        result[region] = {
            'total_cost': Decimal(str(round(data['total_cost'], 2))),
            'percentage': Decimal(str(round((data['total_cost'] / total_cost * 100) if total_cost > 0 else 0, 2))),
            'service_count': len(data['services'])
        }
    
    # Sort by total cost
    sorted_regions = sorted(result.items(), key=lambda x: x[1]['total_cost'], reverse=True)
    
    return {
        'regional_breakdown': dict(sorted_regions),
        'primary_region': sorted_regions[0][0] if sorted_regions else None,
        'region_count': len(regional_costs),
        'total_cost': Decimal(str(round(total_cost, 2)))
    }


def generate_optimization_recommendations(cost_data):
    """
    Generate cost optimization recommendations
    """
    recommendations = []
    
    # Analyze for high-cost resources
    resource_costs = {}
    for record in cost_data:
        resource_id = record.get('resource_id')
        if resource_id:
            cost = float(record.get('cost_amount', 0))
            if resource_id not in resource_costs:
                resource_costs[resource_id] = {
                    'total_cost': 0,
                    'service': record.get('service_name'),
                    'region': record.get('region')
                }
            resource_costs[resource_id]['total_cost'] += cost
    
    # Generate recommendations for high-cost resources
    sorted_resources = sorted(resource_costs.items(), key=lambda x: x[1]['total_cost'], reverse=True)
    
    for resource_id, data in sorted_resources[:10]:  # Top 10 expensive resources
        if data['total_cost'] > 100:  # Threshold for recommendations
            recommendation = {
                'resource_id': resource_id,
                'recommendation_type': 'cost_review',
                'service': data['service'],
                'region': data['region'],
                'current_cost': Decimal(str(round(data['total_cost'], 2))),
                'estimated_savings': Decimal(str(round(data['total_cost'] * 0.2, 2))),  # Assume 20% potential savings
                'confidence': 'medium',
                'priority': 'high' if data['total_cost'] > 500 else 'medium',
                'description': f"High-cost resource requiring review for optimization opportunities",
                'recommended_action': "Review resource utilization and consider rightsizing or optimization",
                'implementation_effort': 'medium',
                'risk_level': 'low',
                'created_at': datetime.utcnow().isoformat(),
                'status': 'open',
                'implemented': False,
                'tags': {},
                'ttl': int((datetime.utcnow() + timedelta(days=60)).timestamp())
            }
            
            recommendations.append(recommendation)
    
    # Store recommendations in DynamoDB
    if recommendations:
        with recommendations_table.batch_writer() as batch:
            for rec in recommendations:
                batch.put_item(Item=rec)
    
    logger.info(f"Generated {len(recommendations)} optimization recommendations")
    return recommendations


def store_analysis_results(analysis_type, results):
    """
    Store analysis results in DynamoDB
    """
    try:
        period = datetime.utcnow().strftime('%Y-%m-%d')

        record = {
            'analysis_type': analysis_type,
            'period': period,
            'results': results,
            'created_at': datetime.utcnow().isoformat(),
            'ttl': int((datetime.utcnow() + timedelta(days=365)).timestamp())
        }

        cost_analysis_table.put_item(Item=record)
        logger.info(f"Stored {analysis_type} results for {period}")

    except Exception as e:
        logger.error(f"Error storing analysis results: {str(e)}")


def generate_daily_summary():
    """
    Generate daily cost summary report
    """
    try:
        # Get yesterday's data
        yesterday = (datetime.utcnow() - timedelta(days=1)).date()
        cost_data = get_cost_data_for_date(yesterday)

        if not cost_data:
            logger.warning(f"No cost data found for {yesterday}")
            return {'message': f'No data available for {yesterday}'}

        # Calculate daily totals
        total_cost = sum(float(record.get('cost_amount', 0)) for record in cost_data)

        # Service breakdown
        service_costs = {}
        for record in cost_data:
            service = record.get('service_name', 'Unknown')
            cost = float(record.get('cost_amount', 0))
            service_costs[service] = service_costs.get(service, 0) + cost

        # Regional breakdown
        regional_costs = {}
        for record in cost_data:
            region = record.get('region', 'unknown')
            cost = float(record.get('cost_amount', 0))
            regional_costs[region] = regional_costs.get(region, 0) + cost

        summary = {
            'date': yesterday.strftime('%Y-%m-%d'),
            'total_cost': Decimal(str(round(total_cost, 2))),
            'service_breakdown': {k: Decimal(str(round(v, 2))) for k, v in service_costs.items()},
            'regional_breakdown': {k: Decimal(str(round(v, 2))) for k, v in regional_costs.items()},
            'record_count': len(cost_data)
        }

        # Store summary
        store_analysis_results('daily_summary', summary)

        # Send notification
        send_summary_notification('Daily Cost Summary', summary)

        return summary

    except Exception as e:
        logger.error(f"Error generating daily summary: {str(e)}")
        return {'error': str(e)}


def generate_weekly_summary():
    """
    Generate weekly cost summary report
    """
    try:
        # Get last week's data
        end_date = (datetime.utcnow() - timedelta(days=1)).date()
        start_date = end_date - timedelta(days=6)

        weekly_data = []
        for i in range(7):
            date = start_date + timedelta(days=i)
            daily_data = get_cost_data_for_date(date)
            weekly_data.extend(daily_data)

        if not weekly_data:
            logger.warning(f"No cost data found for week {start_date} to {end_date}")
            return {'message': f'No data available for week {start_date} to {end_date}'}

        # Calculate weekly totals and trends
        total_cost = sum(float(record.get('cost_amount', 0)) for record in weekly_data)

        # Daily breakdown
        daily_costs = {}
        for record in weekly_data:
            date = record['timestamp'][:10]
            cost = float(record.get('cost_amount', 0))
            daily_costs[date] = daily_costs.get(date, 0) + cost

        # Calculate week-over-week change (if previous week data exists)
        prev_week_start = start_date - timedelta(days=7)
        prev_week_end = end_date - timedelta(days=7)
        prev_week_data = []

        for i in range(7):
            date = prev_week_start + timedelta(days=i)
            daily_data = get_cost_data_for_date(date)
            prev_week_data.extend(daily_data)

        prev_week_cost = sum(float(record.get('cost_amount', 0)) for record in prev_week_data)
        week_change = ((total_cost - prev_week_cost) / prev_week_cost * 100) if prev_week_cost > 0 else 0

        summary = {
            'week_start': start_date.strftime('%Y-%m-%d'),
            'week_end': end_date.strftime('%Y-%m-%d'),
            'total_cost': Decimal(str(round(total_cost, 2))),
            'average_daily_cost': Decimal(str(round(total_cost / 7, 2))),
            'daily_breakdown': {k: Decimal(str(round(v, 2))) for k, v in daily_costs.items()},
            'week_over_week_change': Decimal(str(round(week_change, 2))),
            'record_count': len(weekly_data)
        }

        # Store summary
        store_analysis_results('weekly_summary', summary)

        # Send notification
        send_summary_notification('Weekly Cost Summary', summary)

        return summary

    except Exception as e:
        logger.error(f"Error generating weekly summary: {str(e)}")
        return {'error': str(e)}


def generate_monthly_summary():
    """
    Generate monthly cost summary report
    """
    try:
        # Get last month's data
        today = datetime.utcnow().date()
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)

        monthly_data = []
        current_date = first_day_last_month
        while current_date <= last_day_last_month:
            daily_data = get_cost_data_for_date(current_date)
            monthly_data.extend(daily_data)
            current_date += timedelta(days=1)

        if not monthly_data:
            logger.warning(f"No cost data found for month {first_day_last_month.strftime('%Y-%m')}")
            return {'message': f'No data available for month {first_day_last_month.strftime("%Y-%m")}'}

        # Calculate monthly totals
        total_cost = sum(float(record.get('cost_amount', 0)) for record in monthly_data)
        days_in_month = (last_day_last_month - first_day_last_month).days + 1

        # Service and regional breakdowns
        service_costs = {}
        regional_costs = {}

        for record in monthly_data:
            service = record.get('service_name', 'Unknown')
            region = record.get('region', 'unknown')
            cost = float(record.get('cost_amount', 0))

            service_costs[service] = service_costs.get(service, 0) + cost
            regional_costs[region] = regional_costs.get(region, 0) + cost

        summary = {
            'month': first_day_last_month.strftime('%Y-%m'),
            'total_cost': Decimal(str(round(total_cost, 2))),
            'average_daily_cost': Decimal(str(round(total_cost / days_in_month, 2))),
            'days_in_month': days_in_month,
            'service_breakdown': {k: Decimal(str(round(v, 2))) for k, v in service_costs.items()},
            'regional_breakdown': {k: Decimal(str(round(v, 2))) for k, v in regional_costs.items()},
            'record_count': len(monthly_data)
        }

        # Store summary
        store_analysis_results('monthly_summary', summary)

        # Send notification
        send_summary_notification('Monthly Cost Summary', summary)

        return summary

    except Exception as e:
        logger.error(f"Error generating monthly summary: {str(e)}")
        return {'error': str(e)}


def get_cost_data_for_date(date):
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
        logger.error(f"Error retrieving cost data for {date}: {str(e)}")
        return []


def send_summary_notification(subject, summary):
    """
    Send summary notification via SNS
    """
    try:
        message = {
            'subject': subject,
            'summary': summary,
            'timestamp': datetime.utcnow().isoformat()
        }

        sns.publish(
            TopicArn=REPORTS_TOPIC_ARN,
            Subject=subject,
            Message=json.dumps(message, default=decimal_default)
        )

        logger.info(f"Sent {subject} notification")

    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
