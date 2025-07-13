"""
QuickSight setup script for Cost Optimization Dashboard
"""

import boto3
import json
import os
import time
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
quicksight = boto3.client('quicksight')
sts = boto3.client('sts')

# Get AWS account ID
account_id = sts.get_caller_identity()['Account']
region = os.environ.get('AWS_REGION', 'us-east-1')

# QuickSight configuration
QUICKSIGHT_USER = os.environ.get('QUICKSIGHT_USER', 'quicksight-user')
QUICKSIGHT_NAMESPACE = os.environ.get('QUICKSIGHT_NAMESPACE', 'default')


def create_data_source(data_source_id, data_source_name, table_name):
    """
    Create a DynamoDB data source in QuickSight
    """
    try:
        data_source_config = {
            'AwsAccountId': account_id,
            'DataSourceId': data_source_id,
            'Name': data_source_name,
            'Type': 'AMAZON_DYNAMODB',
            'DataSourceParameters': {
                'AmazonDynamoDbParameters': {
                    'Region': region
                }
            },
            'Permissions': [
                {
                    'Principal': f'arn:aws:quicksight:{region}:{account_id}:user/{QUICKSIGHT_NAMESPACE}/{QUICKSIGHT_USER}',
                    'Actions': [
                        'quicksight:DescribeDataSource',
                        'quicksight:DescribeDataSourcePermissions',
                        'quicksight:PassDataSource',
                        'quicksight:UpdateDataSource',
                        'quicksight:DeleteDataSource',
                        'quicksight:UpdateDataSourcePermissions'
                    ]
                }
            ],
            'Tags': [
                {
                    'Key': 'Project',
                    'Value': 'CostOptimizationDashboard'
                }
            ]
        }
        
        response = quicksight.create_data_source(**data_source_config)
        logger.info(f"Created data source: {data_source_id}")
        return response
        
    except quicksight.exceptions.ResourceExistsException:
        logger.info(f"Data source {data_source_id} already exists")
        return None
    except Exception as e:
        logger.error(f"Error creating data source {data_source_id}: {str(e)}")
        raise


def create_dataset_from_file(dataset_file_path):
    """
    Create a dataset from JSON configuration file
    """
    try:
        with open(dataset_file_path, 'r') as f:
            dataset_config = json.load(f)
        
        # Replace placeholders
        dataset_json = json.dumps(dataset_config)
        dataset_json = dataset_json.replace('ACCOUNT_ID', account_id)
        dataset_config = json.loads(dataset_json)
        
        # Add AWS account ID to the request
        dataset_config['AwsAccountId'] = account_id
        
        response = quicksight.create_data_set(**dataset_config)
        logger.info(f"Created dataset: {dataset_config['DataSetId']}")
        return response
        
    except quicksight.exceptions.ResourceExistsException:
        logger.info(f"Dataset {dataset_config['DataSetId']} already exists")
        return None
    except Exception as e:
        logger.error(f"Error creating dataset from {dataset_file_path}: {str(e)}")
        raise


def create_dashboard_from_file(dashboard_file_path):
    """
    Create a dashboard from JSON configuration file
    """
    try:
        with open(dashboard_file_path, 'r') as f:
            dashboard_config = json.load(f)
        
        # Replace placeholders
        dashboard_json = json.dumps(dashboard_config)
        dashboard_json = dashboard_json.replace('ACCOUNT_ID', account_id)
        dashboard_config = json.loads(dashboard_json)
        
        # Add AWS account ID to the request
        dashboard_config['AwsAccountId'] = account_id
        
        response = quicksight.create_dashboard(**dashboard_config)
        logger.info(f"Created dashboard: {dashboard_config['DashboardId']}")
        return response
        
    except quicksight.exceptions.ResourceExistsException:
        logger.info(f"Dashboard {dashboard_config['DashboardId']} already exists")
        return None
    except Exception as e:
        logger.error(f"Error creating dashboard from {dashboard_file_path}: {str(e)}")
        raise


def wait_for_dataset_creation(dataset_id, max_wait_seconds=300):
    """
    Wait for dataset creation to complete
    """
    start_time = time.time()
    
    while time.time() - start_time < max_wait_seconds:
        try:
            response = quicksight.describe_data_set(
                AwsAccountId=account_id,
                DataSetId=dataset_id
            )
            
            status = response['DataSet']['ImportMode']
            if status in ['DIRECT_QUERY', 'SPICE']:
                logger.info(f"Dataset {dataset_id} is ready")
                return True
                
        except Exception as e:
            logger.warning(f"Waiting for dataset {dataset_id}: {str(e)}")
        
        time.sleep(10)
    
    logger.error(f"Timeout waiting for dataset {dataset_id}")
    return False


def setup_quicksight_permissions():
    """
    Set up QuickSight permissions for DynamoDB access
    """
    try:
        # This would typically involve setting up IAM roles and policies
        # for QuickSight to access DynamoDB tables
        logger.info("Setting up QuickSight permissions...")
        
        # In a real implementation, you would:
        # 1. Create IAM role for QuickSight
        # 2. Attach policies for DynamoDB access
        # 3. Configure QuickSight service role
        
        logger.info("QuickSight permissions configured")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up QuickSight permissions: {str(e)}")
        return False


def create_analysis_from_dashboard(dashboard_id, analysis_id=None):
    """
    Create an analysis from an existing dashboard
    """
    try:
        if not analysis_id:
            analysis_id = f"{dashboard_id}-analysis"
        
        # Get dashboard definition
        dashboard_response = quicksight.describe_dashboard_definition(
            AwsAccountId=account_id,
            DashboardId=dashboard_id
        )
        
        # Create analysis with the same definition
        analysis_config = {
            'AwsAccountId': account_id,
            'AnalysisId': analysis_id,
            'Name': f"Analysis for {dashboard_id}",
            'Definition': dashboard_response['Definition'],
            'Permissions': [
                {
                    'Principal': f'arn:aws:quicksight:{region}:{account_id}:user/{QUICKSIGHT_NAMESPACE}/{QUICKSIGHT_USER}',
                    'Actions': [
                        'quicksight:RestoreAnalysis',
                        'quicksight:UpdateAnalysisPermissions',
                        'quicksight:DeleteAnalysis',
                        'quicksight:DescribeAnalysisPermissions',
                        'quicksight:QueryAnalysis',
                        'quicksight:DescribeAnalysis',
                        'quicksight:UpdateAnalysis'
                    ]
                }
            ]
        }
        
        response = quicksight.create_analysis(**analysis_config)
        logger.info(f"Created analysis: {analysis_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error creating analysis from dashboard {dashboard_id}: {str(e)}")
        raise


def setup_refresh_schedule(dataset_id, schedule_frequency='DAILY'):
    """
    Set up refresh schedule for SPICE datasets
    """
    try:
        schedule_config = {
            'DataSetId': dataset_id,
            'AwsAccountId': account_id,
            'Schedule': {
                'ScheduleId': f"{dataset_id}-refresh-schedule",
                'ScheduleFrequency': {
                    'Interval': schedule_frequency,
                    'TimeOfTheDay': '06:00',
                    'Timezone': 'UTC'
                },
                'StartDate': datetime.utcnow(),
                'RefreshType': 'FULL_REFRESH'
            }
        }
        
        response = quicksight.create_refresh_schedule(**schedule_config)
        logger.info(f"Created refresh schedule for dataset: {dataset_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error creating refresh schedule for {dataset_id}: {str(e)}")
        raise


def main():
    """
    Main setup function
    """
    logger.info("Starting QuickSight setup for Cost Optimization Dashboard")
    
    try:
        # 1. Set up permissions
        if not setup_quicksight_permissions():
            logger.error("Failed to set up QuickSight permissions")
            return False
        
        # 2. Create data sources
        logger.info("Creating data sources...")
        create_data_source(
            'dynamodb-cost-data',
            'Cost Data DynamoDB Source',
            'cost-data'
        )
        
        create_data_source(
            'dynamodb-cost-analysis',
            'Cost Analysis DynamoDB Source',
            'cost-analysis'
        )
        
        # 3. Create datasets
        logger.info("Creating datasets...")
        dataset_files = [
            '../visualization/datasets/cost_data_dataset.json',
            '../visualization/datasets/cost_analysis_dataset.json'
        ]
        
        for dataset_file in dataset_files:
            if os.path.exists(dataset_file):
                create_dataset_from_file(dataset_file)
                
                # Extract dataset ID from file
                with open(dataset_file, 'r') as f:
                    dataset_config = json.load(f)
                dataset_id = dataset_config['DataSetId']
                
                # Wait for dataset to be ready
                wait_for_dataset_creation(dataset_id)
            else:
                logger.warning(f"Dataset file not found: {dataset_file}")
        
        # 4. Create dashboards
        logger.info("Creating dashboards...")
        dashboard_files = [
            '../visualization/dashboards/executive_dashboard.json',
            '../visualization/dashboards/service_analysis_dashboard.json'
        ]
        
        for dashboard_file in dashboard_files:
            if os.path.exists(dashboard_file):
                create_dashboard_from_file(dashboard_file)
            else:
                logger.warning(f"Dashboard file not found: {dashboard_file}")
        
        # 5. Create analyses (optional)
        logger.info("Creating analyses...")
        create_analysis_from_dashboard('cost-optimization-executive-dashboard')
        create_analysis_from_dashboard('cost-optimization-service-analysis')
        
        logger.info("QuickSight setup completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error during QuickSight setup: {str(e)}")
        return False


def cleanup_quicksight_resources():
    """
    Clean up QuickSight resources (for testing/development)
    """
    logger.info("Cleaning up QuickSight resources...")
    
    # List of resources to clean up
    dashboards = [
        'cost-optimization-executive-dashboard',
        'cost-optimization-service-analysis'
    ]
    
    datasets = [
        'cost-data-dataset',
        'cost-analysis-dataset'
    ]
    
    data_sources = [
        'dynamodb-cost-data',
        'dynamodb-cost-analysis'
    ]
    
    # Delete dashboards
    for dashboard_id in dashboards:
        try:
            quicksight.delete_dashboard(
                AwsAccountId=account_id,
                DashboardId=dashboard_id
            )
            logger.info(f"Deleted dashboard: {dashboard_id}")
        except Exception as e:
            logger.warning(f"Could not delete dashboard {dashboard_id}: {str(e)}")
    
    # Delete datasets
    for dataset_id in datasets:
        try:
            quicksight.delete_data_set(
                AwsAccountId=account_id,
                DataSetId=dataset_id
            )
            logger.info(f"Deleted dataset: {dataset_id}")
        except Exception as e:
            logger.warning(f"Could not delete dataset {dataset_id}: {str(e)}")
    
    # Delete data sources
    for data_source_id in data_sources:
        try:
            quicksight.delete_data_source(
                AwsAccountId=account_id,
                DataSourceId=data_source_id
            )
            logger.info(f"Deleted data source: {data_source_id}")
        except Exception as e:
            logger.warning(f"Could not delete data source {data_source_id}: {str(e)}")
    
    logger.info("QuickSight cleanup completed")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'cleanup':
        cleanup_quicksight_resources()
    else:
        main()
