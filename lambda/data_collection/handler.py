"""
AWS Cost Data Collection Lambda Function
Collects cost and usage data from AWS Cost Explorer API and CloudWatch metrics
"""

import json
import os
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from typing import Dict, List, Any
from utils import (
    DecimalEncoder,
    format_cost_record,
    format_usage_record,
    batch_write_to_dynamodb,
    get_cost_explorer_filters,
    validate_cost_data,
    calculate_date_ranges,
    get_cloudwatch_metric_config
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ce_client = boto3.client('ce')  # Cost Explorer
cloudwatch_client = boto3.client('cloudwatch')
dynamodb = boto3.resource('dynamodb')

# Get table names from environment variables
COST_DATA_TABLE = os.environ['COST_DATA_TABLE']
CONFIG_TABLE = os.environ['CONFIG_TABLE']

# Initialize DynamoDB tables
cost_data_table = dynamodb.Table(COST_DATA_TABLE)
config_table = dynamodb.Table(CONFIG_TABLE)


def lambda_handler(event, context):
    """
    Main Lambda handler for cost data collection
    """
    try:
        logger.info("Starting cost data collection")
        
        # Get collection configuration
        config = get_collection_config()
        
        # Collect cost data from Cost Explorer
        cost_data = collect_cost_explorer_data(config)
        
        # Collect usage metrics from CloudWatch
        usage_data = collect_cloudwatch_metrics(config)
        
        # Store data in DynamoDB
        store_cost_data(cost_data)
        store_usage_data(usage_data)
        
        logger.info(f"Successfully collected and stored {len(cost_data)} cost records and {len(usage_data)} usage records")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Cost data collection completed successfully',
                'cost_records': len(cost_data),
                'usage_records': len(usage_data),
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error in cost data collection: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }


def get_collection_config():
    """
    Get collection configuration from DynamoDB config table
    """
    try:
        response = config_table.get_item(
            Key={'config_type': 'data_collection'}
        )
        
        if 'Item' in response:
            return response['Item']
        else:
            # Return default configuration
            return {
                'lookback_days': 7,
                'granularity': 'DAILY',
                'metrics': ['BlendedCost', 'UsageQuantity'],
                'group_by': [
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                    {'Type': 'DIMENSION', 'Key': 'REGION'}
                ]
            }
    except Exception as e:
        logger.warning(f"Could not load config, using defaults: {str(e)}")
        return {
            'lookback_days': 7,
            'granularity': 'DAILY',
            'metrics': ['BlendedCost', 'UsageQuantity']
        }


def collect_cost_explorer_data(config):
    """
    Collect cost and usage data from AWS Cost Explorer API
    """
    cost_data = []
    
    # Calculate date range
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=config.get('lookback_days', 7))
    
    try:
        # Get cost and usage data
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity=config.get('granularity', 'DAILY'),
            Metrics=config.get('metrics', ['BlendedCost']),
            GroupBy=config.get('group_by', [
                {'Type': 'DIMENSION', 'Key': 'SERVICE'}
            ])
        )
        
        # Process the response
        for result in response.get('ResultsByTime', []):
            time_period = result['TimePeriod']
            
            for group in result.get('Groups', []):
                keys = group['Keys']
                metrics = group['Metrics']
                
                # Extract service and region from keys
                service = keys[0] if len(keys) > 0 else 'Unknown'
                region = keys[1] if len(keys) > 1 else 'global'
                
                # Create cost record
                cost_record = {
                    'service_id': f"{service}#{region}",
                    'timestamp': time_period['Start'],
                    'service_name': service,
                    'region': region,
                    'cost_amount': Decimal(str(metrics.get('BlendedCost', {}).get('Amount', '0'))),
                    'usage_quantity': Decimal(str(metrics.get('UsageQuantity', {}).get('Amount', '0'))),
                    'usage_unit': metrics.get('UsageQuantity', {}).get('Unit', ''),
                    'currency': metrics.get('BlendedCost', {}).get('Unit', 'USD'),
                    'collection_timestamp': datetime.utcnow().isoformat(),
                    'ttl': int((datetime.utcnow() + timedelta(days=90)).timestamp())
                }
                
                cost_data.append(cost_record)
        
        logger.info(f"Collected {len(cost_data)} cost records from Cost Explorer")
        return cost_data
        
    except Exception as e:
        logger.error(f"Error collecting Cost Explorer data: {str(e)}")
        return []


def collect_cloudwatch_metrics(config):
    """
    Collect usage metrics from CloudWatch
    """
    usage_data = []

    # Get metrics configuration
    metrics_config = get_cloudwatch_metric_config()

    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=config.get('cloudwatch_hours', 24))

    try:
        for service, metrics in metrics_config.items():
            namespace = f"AWS/{service}"

            for metric in metrics:
                try:
                    # Get metric statistics
                    response = cloudwatch_client.get_metric_statistics(
                        Namespace=namespace,
                        MetricName=metric['metric_name'],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1 hour
                        Statistics=[metric['statistic']]
                    )

                    # Process datapoints
                    for datapoint in response.get('Datapoints', []):
                        usage_record = format_usage_record(
                            namespace=namespace,
                            metric_name=metric['metric_name'],
                            datapoint=datapoint
                        )
                        usage_data.append(usage_record)

                except Exception as metric_error:
                    logger.warning(f"Error collecting metric {metric['metric_name']} from {namespace}: {str(metric_error)}")
                    continue

        logger.info(f"Collected {len(usage_data)} usage records from CloudWatch")
        return usage_data

    except Exception as e:
        logger.error(f"Error collecting CloudWatch metrics: {str(e)}")
        return []


def store_cost_data(cost_data):
    """
    Store cost data in DynamoDB with validation
    """
    if not cost_data:
        return

    try:
        # Validate records before storing
        validated_records = []
        for record in cost_data:
            try:
                validate_cost_data(record)
                validated_records.append(record)
            except ValueError as e:
                logger.warning(f"Skipping invalid cost record: {str(e)}")
                continue

        # Batch write to DynamoDB
        batch_write_to_dynamodb(cost_data_table, validated_records)

    except Exception as e:
        logger.error(f"Error storing cost data: {str(e)}")
        raise


def store_usage_data(usage_data):
    """
    Store usage data in DynamoDB
    """
    if not usage_data:
        return

    try:
        # Batch write to DynamoDB
        batch_write_to_dynamodb(cost_data_table, usage_data)

    except Exception as e:
        logger.error(f"Error storing usage data: {str(e)}")
        raise
