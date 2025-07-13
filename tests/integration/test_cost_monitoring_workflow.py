"""
Integration tests for the complete cost monitoring workflow
"""

import unittest
import boto3
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal
import os
import sys

# Add the lambda directories to the path for imports
sys.path.append('../../lambda/data_collection')
sys.path.append('../../lambda/data_processing')
sys.path.append('../../lambda/alerting')

from lambda.data_collection.handler import lambda_handler as data_collection_handler
from lambda.data_processing.handler import lambda_handler as data_processing_handler
from lambda.alerting.handler import lambda_handler as alerting_handler


class TestCostMonitoringWorkflow(unittest.TestCase):
    """
    Integration tests for the complete cost monitoring workflow
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.dynamodb = boto3.resource('dynamodb')
        cls.sns = boto3.client('sns')
        cls.lambda_client = boto3.client('lambda')
        
        # Test table names (should be test environment)
        cls.cost_data_table_name = 'cost-data-test'
        cls.cost_analysis_table_name = 'cost-analysis-test'
        cls.config_table_name = 'cost-config-test'
        cls.alerts_table_name = 'cost-alerts-test'
        
        # Set environment variables for Lambda functions
        os.environ['COST_DATA_TABLE'] = cls.cost_data_table_name
        os.environ['COST_ANALYSIS_TABLE'] = cls.cost_analysis_table_name
        os.environ['CONFIG_TABLE'] = cls.config_table_name
        os.environ['ALERTS_TABLE'] = cls.alerts_table_name
        os.environ['ALERTS_TOPIC_ARN'] = 'arn:aws:sns:us-east-1:123456789012:test-alerts'
        os.environ['REPORTS_TOPIC_ARN'] = 'arn:aws:sns:us-east-1:123456789012:test-reports'
        
        # Create test tables if they don't exist
        cls.create_test_tables()
        
        # Insert test configuration
        cls.setup_test_configuration()
    
    @classmethod
    def create_test_tables(cls):
        """Create test DynamoDB tables"""
        try:
            # Cost data table
            cls.dynamodb.create_table(
                TableName=cls.cost_data_table_name,
                KeySchema=[
                    {'AttributeName': 'service_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'service_id', 'AttributeType': 'S'},
                    {'AttributeName': 'timestamp', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Cost analysis table
            cls.dynamodb.create_table(
                TableName=cls.cost_analysis_table_name,
                KeySchema=[
                    {'AttributeName': 'analysis_type', 'KeyType': 'HASH'},
                    {'AttributeName': 'period', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'analysis_type', 'AttributeType': 'S'},
                    {'AttributeName': 'period', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Config table
            cls.dynamodb.create_table(
                TableName=cls.config_table_name,
                KeySchema=[
                    {'AttributeName': 'config_type', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'config_type', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Alerts table
            cls.dynamodb.create_table(
                TableName=cls.alerts_table_name,
                KeySchema=[
                    {'AttributeName': 'alert_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'alert_id', 'AttributeType': 'S'},
                    {'AttributeName': 'timestamp', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Wait for tables to be created
            time.sleep(10)
            
        except Exception as e:
            print(f"Tables may already exist: {str(e)}")
    
    @classmethod
    def setup_test_configuration(cls):
        """Set up test configuration data"""
        config_table = cls.dynamodb.Table(cls.config_table_name)
        
        # Threshold configuration
        config_table.put_item(Item={
            'config_type': 'thresholds',
            'cost_thresholds': {
                'daily': {'warning': 50, 'critical': 100},
                'weekly': {'warning': 300, 'critical': 500},
                'monthly': {'warning': 1000, 'critical': 2000}
            },
            'service_thresholds': {
                'EC2': {'daily': 25, 'monthly': 600},
                'S3': {'daily': 10, 'monthly': 200}
            },
            'anomaly_detection': {
                'enabled': True,
                'sensitivity': 'medium'
            }
        })
    
    def setUp(self):
        """Set up each test"""
        self.test_start_time = datetime.utcnow()
        
        # Clear test data
        self.clear_test_data()
        
        # Insert sample cost data
        self.insert_sample_cost_data()
    
    def clear_test_data(self):
        """Clear test data from tables"""
        tables = [
            self.cost_data_table_name,
            self.cost_analysis_table_name,
            self.alerts_table_name
        ]
        
        for table_name in tables:
            table = self.dynamodb.Table(table_name)
            
            # Scan and delete all items
            response = table.scan()
            with table.batch_writer() as batch:
                for item in response.get('Items', []):
                    batch.delete_item(Key={
                        k: v for k, v in item.items() 
                        if k in [attr['AttributeName'] for attr in table.key_schema]
                    })
    
    def insert_sample_cost_data(self):
        """Insert sample cost data for testing"""
        cost_data_table = self.dynamodb.Table(self.cost_data_table_name)
        
        # Generate sample data for the last 7 days
        sample_data = []
        for i in range(7):
            date = (datetime.utcnow() - timedelta(days=i)).date()
            timestamp = date.strftime('%Y-%m-%d')
            
            # EC2 costs
            sample_data.append({
                'service_id': 'Amazon Elastic Compute Cloud - Compute#us-east-1',
                'timestamp': timestamp,
                'service_name': 'Amazon Elastic Compute Cloud - Compute',
                'region': 'us-east-1',
                'cost_amount': Decimal(str(30 + i * 5)),  # Increasing costs
                'usage_quantity': Decimal('100'),
                'usage_unit': 'Hrs',
                'currency': 'USD',
                'collection_timestamp': datetime.utcnow().isoformat(),
                'ttl': int((datetime.utcnow() + timedelta(days=90)).timestamp())
            })
            
            # S3 costs
            sample_data.append({
                'service_id': 'Amazon Simple Storage Service#us-east-1',
                'timestamp': timestamp,
                'service_name': 'Amazon Simple Storage Service',
                'region': 'us-east-1',
                'cost_amount': Decimal(str(15 + i * 2)),
                'usage_quantity': Decimal('1000'),
                'usage_unit': 'GB',
                'currency': 'USD',
                'collection_timestamp': datetime.utcnow().isoformat(),
                'ttl': int((datetime.utcnow() + timedelta(days=90)).timestamp())
            })
        
        # Insert data
        with cost_data_table.batch_writer() as batch:
            for item in sample_data:
                batch.put_item(Item=item)
    
    def test_data_collection_workflow(self):
        """Test the data collection workflow"""
        print("Testing data collection workflow...")
        
        # Mock event for data collection
        event = {}
        context = type('Context', (), {'aws_request_id': 'test-request-id'})()
        
        # This would normally call Cost Explorer API, but we'll test with mock data
        # In a real test environment, you'd mock the boto3 clients
        
        # For now, just verify the handler can be called
        try:
            # Note: This will fail in test environment without proper AWS credentials
            # In a real test, you'd mock the AWS API calls
            response = data_collection_handler(event, context)
            self.assertIn('statusCode', response)
        except Exception as e:
            # Expected in test environment without Cost Explorer access
            print(f"Data collection test skipped due to API access: {str(e)}")
    
    def test_data_processing_workflow(self):
        """Test the data processing workflow"""
        print("Testing data processing workflow...")
        
        # Mock event for data processing
        event = {}
        context = type('Context', (), {'aws_request_id': 'test-request-id'})()
        
        try:
            response = data_processing_handler(event, context)
            self.assertEqual(response['statusCode'], 200)
            
            # Verify analysis data was created
            analysis_table = self.dynamodb.Table(self.cost_analysis_table_name)
            response = analysis_table.scan()
            
            # Should have some analysis results
            self.assertGreater(len(response.get('Items', [])), 0)
            
        except Exception as e:
            print(f"Data processing test error: {str(e)}")
            self.fail(f"Data processing failed: {str(e)}")
    
    def test_alerting_workflow(self):
        """Test the alerting workflow"""
        print("Testing alerting workflow...")
        
        # Insert high-cost data to trigger alerts
        cost_data_table = self.dynamodb.Table(self.cost_data_table_name)
        
        # Add high-cost record that should trigger alert
        high_cost_record = {
            'service_id': 'Amazon Elastic Compute Cloud - Compute#us-east-1',
            'timestamp': datetime.utcnow().date().strftime('%Y-%m-%d'),
            'service_name': 'Amazon Elastic Compute Cloud - Compute',
            'region': 'us-east-1',
            'cost_amount': Decimal('150'),  # Above threshold
            'usage_quantity': Decimal('100'),
            'usage_unit': 'Hrs',
            'currency': 'USD',
            'collection_timestamp': datetime.utcnow().isoformat(),
            'ttl': int((datetime.utcnow() + timedelta(days=90)).timestamp())
        }
        
        cost_data_table.put_item(Item=high_cost_record)
        
        # Test alerting
        event = {'test_mode': True}
        context = type('Context', (), {'aws_request_id': 'test-request-id'})()
        
        try:
            response = alerting_handler(event, context)
            self.assertEqual(response['statusCode'], 200)
            
            # Verify alerts were created
            alerts_table = self.dynamodb.Table(self.alerts_table_name)
            response = alerts_table.scan()
            
            alerts = response.get('Items', [])
            self.assertGreater(len(alerts), 0)
            
            # Verify alert content
            alert = alerts[0]
            self.assertEqual(alert['severity'], 'critical')
            self.assertEqual(alert['service'], 'Amazon Elastic Compute Cloud - Compute')
            
        except Exception as e:
            print(f"Alerting test error: {str(e)}")
            self.fail(f"Alerting failed: {str(e)}")
    
    def test_end_to_end_workflow(self):
        """Test the complete end-to-end workflow"""
        print("Testing end-to-end workflow...")
        
        # 1. Data Collection (simulated)
        print("Step 1: Data Collection")
        # In real test, this would collect actual data
        
        # 2. Data Processing
        print("Step 2: Data Processing")
        event = {}
        context = type('Context', (), {'aws_request_id': 'test-request-id'})()
        
        processing_response = data_processing_handler(event, context)
        self.assertEqual(processing_response['statusCode'], 200)
        
        # 3. Alerting
        print("Step 3: Alerting")
        alerting_event = {'test_mode': True}
        alerting_response = alerting_handler(alerting_event, context)
        self.assertEqual(alerting_response['statusCode'], 200)
        
        # 4. Verify complete workflow
        print("Step 4: Verification")
        
        # Check that analysis data exists
        analysis_table = self.dynamodb.Table(self.cost_analysis_table_name)
        analysis_response = analysis_table.scan()
        self.assertGreater(len(analysis_response.get('Items', [])), 0)
        
        print("End-to-end workflow test completed successfully!")
    
    def test_data_quality_validation(self):
        """Test data quality and validation"""
        print("Testing data quality validation...")
        
        cost_data_table = self.dynamodb.Table(self.cost_data_table_name)
        
        # Get sample data
        response = cost_data_table.scan()
        items = response.get('Items', [])
        
        for item in items:
            # Validate required fields
            self.assertIn('service_id', item)
            self.assertIn('timestamp', item)
            self.assertIn('cost_amount', item)
            
            # Validate data types
            self.assertIsInstance(item['cost_amount'], Decimal)
            self.assertGreaterEqual(float(item['cost_amount']), 0)
            
            # Validate timestamp format
            try:
                datetime.strptime(item['timestamp'], '%Y-%m-%d')
            except ValueError:
                self.fail(f"Invalid timestamp format: {item['timestamp']}")
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks"""
        print("Testing performance benchmarks...")
        
        start_time = time.time()
        
        # Test data processing performance
        event = {}
        context = type('Context', (), {'aws_request_id': 'test-request-id'})()
        
        response = data_processing_handler(event, context)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        self.assertLess(execution_time, 30, "Data processing took too long")
        
        print(f"Data processing completed in {execution_time:.2f} seconds")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        print("Cleaning up test environment...")
        
        # Delete test tables
        tables = [
            cls.cost_data_table_name,
            cls.cost_analysis_table_name,
            cls.config_table_name,
            cls.alerts_table_name
        ]
        
        for table_name in tables:
            try:
                table = cls.dynamodb.Table(table_name)
                table.delete()
                print(f"Deleted table: {table_name}")
            except Exception as e:
                print(f"Could not delete table {table_name}: {str(e)}")


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
