"""
Utility functions for cost data collection
"""

import boto3
import json
from datetime import datetime, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder for Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def get_aws_services_list():
    """
    Get list of AWS services for cost monitoring
    """
    return [
        'Amazon Elastic Compute Cloud - Compute',
        'Amazon Simple Storage Service',
        'AWS Lambda',
        'Amazon Relational Database Service',
        'Amazon CloudWatch',
        'Amazon DynamoDB',
        'Elastic Load Balancing',
        'Amazon CloudFront',
        'Amazon Route 53',
        'Amazon Simple Notification Service',
        'Amazon Simple Queue Service',
        'Amazon API Gateway',
        'AWS Key Management Service',
        'Amazon Elastic Container Service',
        'Amazon Elastic Kubernetes Service',
        'Amazon Redshift',
        'Amazon ElastiCache',
        'Amazon Elasticsearch Service',
        'AWS Glue',
        'Amazon Kinesis'
    ]


def get_aws_regions_list():
    """
    Get list of AWS regions for cost monitoring
    """
    return [
        'us-east-1',
        'us-east-2',
        'us-west-1',
        'us-west-2',
        'eu-west-1',
        'eu-west-2',
        'eu-west-3',
        'eu-central-1',
        'ap-southeast-1',
        'ap-southeast-2',
        'ap-northeast-1',
        'ap-northeast-2',
        'ap-south-1',
        'ca-central-1',
        'sa-east-1'
    ]


def format_cost_record(service, region, time_period, metrics, tags=None):
    """
    Format a cost record for DynamoDB storage
    """
    return {
        'service_id': f"{service}#{region}",
        'timestamp': time_period,
        'service_name': service,
        'region': region,
        'cost_amount': Decimal(str(metrics.get('BlendedCost', {}).get('Amount', '0'))),
        'usage_quantity': Decimal(str(metrics.get('UsageQuantity', {}).get('Amount', '0'))),
        'usage_unit': metrics.get('UsageQuantity', {}).get('Unit', ''),
        'currency': metrics.get('BlendedCost', {}).get('Unit', 'USD'),
        'tags': tags or {},
        'collection_timestamp': datetime.utcnow().isoformat(),
        'ttl': int((datetime.utcnow() + timedelta(days=90)).timestamp())
    }


def format_usage_record(namespace, metric_name, datapoint, dimensions=None):
    """
    Format a usage record for DynamoDB storage
    """
    return {
        'service_id': f"{namespace}#{metric_name}",
        'timestamp': datapoint['Timestamp'].isoformat(),
        'metric_name': metric_name,
        'namespace': namespace,
        'value': Decimal(str(datapoint.get('Average', datapoint.get('Sum', datapoint.get('Maximum', 0))))),
        'unit': datapoint.get('Unit', ''),
        'dimensions': dimensions or {},
        'collection_timestamp': datetime.utcnow().isoformat(),
        'ttl': int((datetime.utcnow() + timedelta(days=30)).timestamp())
    }


def batch_write_to_dynamodb(table, items, batch_size=25):
    """
    Write items to DynamoDB in batches
    """
    if not items:
        return
    
    try:
        with table.batch_writer() as batch:
            for i, item in enumerate(items):
                batch.put_item(Item=item)
                
                # Log progress for large batches
                if (i + 1) % 100 == 0:
                    logger.info(f"Processed {i + 1}/{len(items)} items")
        
        logger.info(f"Successfully wrote {len(items)} items to {table.table_name}")
        
    except Exception as e:
        logger.error(f"Error writing to DynamoDB: {str(e)}")
        raise


def get_cost_explorer_filters(config):
    """
    Build Cost Explorer filters based on configuration
    """
    filters = {}
    
    # Add service filter if specified
    if 'services' in config:
        filters['Dimensions'] = {
            'Key': 'SERVICE',
            'Values': config['services']
        }
    
    # Add tag filters if specified
    if 'tag_filters' in config:
        tag_filters = []
        for tag_key, tag_values in config['tag_filters'].items():
            tag_filters.append({
                'Key': tag_key,
                'Values': tag_values
            })
        filters['Tags'] = tag_filters
    
    return filters


def validate_cost_data(cost_record):
    """
    Validate cost data record before storage
    """
    required_fields = ['service_id', 'timestamp', 'cost_amount']
    
    for field in required_fields:
        if field not in cost_record:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate cost amount is not negative
    if cost_record['cost_amount'] < 0:
        logger.warning(f"Negative cost amount detected: {cost_record['cost_amount']}")
    
    # Validate timestamp format
    try:
        datetime.fromisoformat(cost_record['timestamp'].replace('Z', '+00:00'))
    except ValueError:
        raise ValueError(f"Invalid timestamp format: {cost_record['timestamp']}")
    
    return True


def calculate_date_ranges(lookback_days, granularity='DAILY'):
    """
    Calculate date ranges for Cost Explorer queries
    """
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=lookback_days)
    
    date_ranges = []
    
    if granularity == 'DAILY':
        current_date = start_date
        while current_date < end_date:
            next_date = current_date + timedelta(days=1)
            date_ranges.append({
                'Start': current_date.strftime('%Y-%m-%d'),
                'End': next_date.strftime('%Y-%m-%d')
            })
            current_date = next_date
    
    elif granularity == 'MONTHLY':
        # For monthly, use full months
        current_date = start_date.replace(day=1)
        while current_date < end_date:
            if current_date.month == 12:
                next_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                next_date = current_date.replace(month=current_date.month + 1)
            
            date_ranges.append({
                'Start': current_date.strftime('%Y-%m-%d'),
                'End': next_date.strftime('%Y-%m-%d')
            })
            current_date = next_date
    
    return date_ranges


def get_cloudwatch_metric_config():
    """
    Get CloudWatch metrics configuration for different services
    """
    return {
        'EC2': [
            {
                'metric_name': 'CPUUtilization',
                'statistic': 'Average',
                'unit': 'Percent'
            },
            {
                'metric_name': 'NetworkIn',
                'statistic': 'Sum',
                'unit': 'Bytes'
            },
            {
                'metric_name': 'NetworkOut',
                'statistic': 'Sum',
                'unit': 'Bytes'
            }
        ],
        'Lambda': [
            {
                'metric_name': 'Invocations',
                'statistic': 'Sum',
                'unit': 'Count'
            },
            {
                'metric_name': 'Duration',
                'statistic': 'Average',
                'unit': 'Milliseconds'
            },
            {
                'metric_name': 'Errors',
                'statistic': 'Sum',
                'unit': 'Count'
            }
        ],
        'RDS': [
            {
                'metric_name': 'CPUUtilization',
                'statistic': 'Average',
                'unit': 'Percent'
            },
            {
                'metric_name': 'DatabaseConnections',
                'statistic': 'Average',
                'unit': 'Count'
            }
        ],
        'DynamoDB': [
            {
                'metric_name': 'ConsumedReadCapacityUnits',
                'statistic': 'Sum',
                'unit': 'Count'
            },
            {
                'metric_name': 'ConsumedWriteCapacityUnits',
                'statistic': 'Sum',
                'unit': 'Count'
            }
        ]
    }
