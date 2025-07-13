"""
DynamoDB utility functions for Cost Optimization Dashboard
"""

import boto3
import json
from datetime import datetime, timedelta
from decimal import Decimal
import random
import uuid

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')

# Table names
COST_DATA_TABLE = 'cost-data'
COST_ANALYSIS_TABLE = 'cost-analysis'
CONFIG_TABLE = 'cost-config'
ALERTS_TABLE = 'cost-alerts'
RECOMMENDATIONS_TABLE = 'cost-recommendations'


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder for Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def create_sample_cost_data(days=30):
    """
    Create sample cost data for testing
    """
    table = dynamodb.Table(COST_DATA_TABLE)
    
    services = [
        'Amazon Elastic Compute Cloud - Compute',
        'Amazon Simple Storage Service',
        'AWS Lambda',
        'Amazon Relational Database Service',
        'Amazon CloudWatch',
        'Amazon DynamoDB'
    ]
    
    regions = ['us-east-1', 'us-west-2', 'eu-west-1']
    environments = ['production', 'staging', 'development']
    teams = ['backend', 'frontend', 'data', 'devops']
    projects = ['web-app', 'mobile-api', 'analytics']
    
    sample_data = []
    
    for day in range(days):
        date = (datetime.utcnow() - timedelta(days=day)).date()
        timestamp = date.strftime('%Y-%m-%d')
        
        for service in services:
            for region in regions:
                # Generate realistic cost data with some variation
                base_cost = random.uniform(10, 500)
                daily_variation = random.uniform(0.8, 1.2)
                cost_amount = Decimal(str(round(base_cost * daily_variation, 2)))
                
                usage_quantity = Decimal(str(round(random.uniform(1, 1000), 2)))
                
                record = {
                    'service_id': f"{service}#{region}",
                    'timestamp': timestamp,
                    'service_name': service,
                    'region': region,
                    'cost_amount': cost_amount,
                    'usage_quantity': usage_quantity,
                    'usage_unit': 'Hrs' if 'Compute' in service else 'GB',
                    'currency': 'USD',
                    'tags': {
                        'Environment': random.choice(environments),
                        'Team': random.choice(teams),
                        'Project': random.choice(projects)
                    },
                    'resource_id': f"resource-{uuid.uuid4().hex[:8]}",
                    'collection_timestamp': datetime.utcnow().isoformat(),
                    'ttl': int((datetime.utcnow() + timedelta(days=90)).timestamp())
                }
                
                sample_data.append(record)
    
    # Batch write to DynamoDB
    with table.batch_writer() as batch:
        for record in sample_data:
            batch.put_item(Item=record)
    
    print(f"Created {len(sample_data)} sample cost records")
    return sample_data


def create_sample_analysis_data():
    """
    Create sample analysis data
    """
    table = dynamodb.Table(COST_ANALYSIS_TABLE)
    
    analysis_types = ['daily_summary', 'weekly_summary', 'monthly_summary', 'trend_analysis']
    
    sample_data = []
    
    # Create daily summaries for last 30 days
    for day in range(30):
        date = (datetime.utcnow() - timedelta(days=day)).date()
        
        record = {
            'analysis_type': 'daily_summary',
            'period': date.strftime('%Y-%m-%d'),
            'total_cost': Decimal(str(round(random.uniform(800, 1500), 2))),
            'service_breakdown': {
                'EC2': Decimal(str(round(random.uniform(200, 600), 2))),
                'S3': Decimal(str(round(random.uniform(50, 200), 2))),
                'Lambda': Decimal(str(round(random.uniform(20, 100), 2))),
                'RDS': Decimal(str(round(random.uniform(100, 400), 2))),
                'Other': Decimal(str(round(random.uniform(100, 300), 2)))
            },
            'regional_breakdown': {
                'us-east-1': Decimal(str(round(random.uniform(400, 800), 2))),
                'us-west-2': Decimal(str(round(random.uniform(200, 400), 2))),
                'eu-west-1': Decimal(str(round(random.uniform(100, 300), 2)))
            },
            'trends': {
                'cost_change_percent': Decimal(str(round(random.uniform(-10, 15), 1))),
                'usage_change_percent': Decimal(str(round(random.uniform(-5, 10), 1))),
                'top_growing_service': random.choice(['EC2', 'Lambda', 'S3', 'RDS']),
                'cost_efficiency_score': Decimal(str(round(random.uniform(70, 95), 1)))
            },
            'recommendations': [
                {
                    'type': 'rightsizing',
                    'resource_id': f"i-{uuid.uuid4().hex[:16]}",
                    'potential_savings': Decimal(str(round(random.uniform(20, 100), 2))),
                    'confidence': random.choice(['high', 'medium', 'low'])
                }
            ],
            'created_at': datetime.utcnow().isoformat(),
            'ttl': int((datetime.utcnow() + timedelta(days=365)).timestamp())
        }
        
        sample_data.append(record)
    
    # Batch write to DynamoDB
    with table.batch_writer() as batch:
        for record in sample_data:
            batch.put_item(Item=record)
    
    print(f"Created {len(sample_data)} sample analysis records")
    return sample_data


def create_sample_alerts():
    """
    Create sample alert data
    """
    table = dynamodb.Table(ALERTS_TABLE)
    
    alert_types = ['threshold_breach', 'anomaly_detection', 'budget_exceeded']
    severities = ['info', 'warning', 'critical']
    services = ['EC2', 'S3', 'Lambda', 'RDS']
    regions = ['us-east-1', 'us-west-2', 'eu-west-1']
    
    sample_data = []
    
    # Create alerts for last 7 days
    for day in range(7):
        for _ in range(random.randint(1, 5)):  # 1-5 alerts per day
            timestamp = (datetime.utcnow() - timedelta(days=day, hours=random.randint(0, 23)))
            service = random.choice(services)
            region = random.choice(regions)
            severity = random.choice(severities)
            
            alert_id = f"alert_{service.lower()}_{region}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            record = {
                'alert_id': alert_id,
                'timestamp': timestamp.isoformat(),
                'alert_type': random.choice(alert_types),
                'severity': severity,
                'service': service,
                'region': region,
                'current_cost': Decimal(str(round(random.uniform(50, 300), 2))),
                'threshold': Decimal(str(round(random.uniform(30, 200), 2))),
                'message': f"{service} costs in {region} exceeded {severity} threshold",
                'status': random.choice(['active', 'acknowledged', 'resolved']),
                'acknowledged': random.choice([True, False]),
                'acknowledged_by': 'admin' if random.choice([True, False]) else None,
                'acknowledged_at': timestamp.isoformat() if random.choice([True, False]) else None,
                'resolved': random.choice([True, False]),
                'resolved_at': timestamp.isoformat() if random.choice([True, False]) else None,
                'notification_sent': True,
                'notification_channels': ['email', 'slack'],
                'ttl': int((datetime.utcnow() + timedelta(days=30)).timestamp())
            }
            
            sample_data.append(record)
    
    # Batch write to DynamoDB
    with table.batch_writer() as batch:
        for record in sample_data:
            batch.put_item(Item=record)
    
    print(f"Created {len(sample_data)} sample alert records")
    return sample_data


def create_sample_recommendations():
    """
    Create sample recommendation data
    """
    table = dynamodb.Table(RECOMMENDATIONS_TABLE)
    
    recommendation_types = ['rightsizing', 'reserved_instances', 'idle_resources', 'storage_optimization']
    services = ['EC2', 'RDS', 'S3', 'Lambda']
    regions = ['us-east-1', 'us-west-2', 'eu-west-1']
    priorities = ['high', 'medium', 'low']
    
    sample_data = []
    
    for _ in range(50):  # Create 50 recommendations
        service = random.choice(services)
        region = random.choice(regions)
        rec_type = random.choice(recommendation_types)
        
        resource_id = f"{service.lower()}-{uuid.uuid4().hex[:8]}"
        
        record = {
            'resource_id': resource_id,
            'recommendation_type': rec_type,
            'service': service,
            'region': region,
            'current_cost': Decimal(str(round(random.uniform(50, 500), 2))),
            'estimated_savings': Decimal(str(round(random.uniform(10, 200), 2))),
            'confidence': random.choice(['high', 'medium', 'low']),
            'priority': random.choice(priorities),
            'description': f"{service} resource can be optimized through {rec_type}",
            'recommended_action': f"Apply {rec_type} optimization",
            'implementation_effort': random.choice(['low', 'medium', 'high']),
            'risk_level': random.choice(['low', 'medium', 'high']),
            'created_at': datetime.utcnow().isoformat(),
            'status': random.choice(['open', 'in_progress', 'implemented', 'dismissed']),
            'implemented': random.choice([True, False]),
            'implemented_at': datetime.utcnow().isoformat() if random.choice([True, False]) else None,
            'actual_savings': Decimal(str(round(random.uniform(5, 150), 2))) if random.choice([True, False]) else None,
            'tags': {
                'Environment': random.choice(['production', 'staging', 'development']),
                'Team': random.choice(['backend', 'frontend', 'data'])
            },
            'ttl': int((datetime.utcnow() + timedelta(days=60)).timestamp())
        }
        
        sample_data.append(record)
    
    # Batch write to DynamoDB
    with table.batch_writer() as batch:
        for record in sample_data:
            batch.put_item(Item=record)
    
    print(f"Created {len(sample_data)} sample recommendation records")
    return sample_data


def query_cost_data_by_service(service_name, region, start_date, end_date):
    """
    Query cost data for a specific service and region
    """
    table = dynamodb.Table(COST_DATA_TABLE)
    
    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('service_id').eq(f"{service_name}#{region}") &
                              boto3.dynamodb.conditions.Key('timestamp').between(start_date, end_date)
    )
    
    return response['Items']


def query_active_alerts():
    """
    Query active alerts
    """
    table = dynamodb.Table(ALERTS_TABLE)
    
    response = table.query(
        IndexName='status-timestamp-index',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('status').eq('active')
    )
    
    return response['Items']


def query_high_priority_recommendations():
    """
    Query high priority recommendations sorted by savings
    """
    table = dynamodb.Table(RECOMMENDATIONS_TABLE)
    
    response = table.query(
        IndexName='priority-savings-index',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('priority').eq('high'),
        ScanIndexForward=False  # Sort by savings descending
    )
    
    return response['Items']


if __name__ == "__main__":
    print("Creating sample data for Cost Optimization Dashboard...")
    
    # Create sample data
    create_sample_cost_data(30)
    create_sample_analysis_data()
    create_sample_alerts()
    create_sample_recommendations()
    
    print("Sample data creation completed!")
    
    # Test some queries
    print("\nTesting queries...")
    
    # Query cost data
    cost_data = query_cost_data_by_service(
        'Amazon Elastic Compute Cloud - Compute',
        'us-east-1',
        '2024-01-01',
        '2024-01-31'
    )
    print(f"Found {len(cost_data)} cost records for EC2 in us-east-1")
    
    # Query active alerts
    active_alerts = query_active_alerts()
    print(f"Found {len(active_alerts)} active alerts")
    
    # Query high priority recommendations
    high_priority_recs = query_high_priority_recommendations()
    print(f"Found {len(high_priority_recs)} high priority recommendations")
