"""
Unit tests for data collection Lambda function
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add lambda directory to path
sys.path.append('../../lambda/data_collection')

from lambda.data_collection.handler import (
    get_collection_config,
    collect_cost_explorer_data,
    collect_cloudwatch_metrics,
    store_cost_data,
    store_usage_data
)


class TestDataCollection(unittest.TestCase):
    """Unit tests for data collection functions"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock environment variables
        os.environ['COST_DATA_TABLE'] = 'test-cost-data'
        os.environ['CONFIG_TABLE'] = 'test-config'
        
        # Mock AWS clients
        self.mock_dynamodb = Mock()
        self.mock_ce_client = Mock()
        self.mock_cloudwatch_client = Mock()
    
    @patch('lambda.data_collection.handler.config_table')
    def test_get_collection_config_success(self, mock_config_table):
        """Test successful configuration retrieval"""
        # Mock DynamoDB response
        mock_config_table.get_item.return_value = {
            'Item': {
                'lookback_days': 7,
                'granularity': 'DAILY',
                'metrics': ['BlendedCost', 'UsageQuantity']
            }
        }
        
        config = get_collection_config()
        
        self.assertEqual(config['lookback_days'], 7)
        self.assertEqual(config['granularity'], 'DAILY')
        self.assertIn('BlendedCost', config['metrics'])
    
    @patch('lambda.data_collection.handler.config_table')
    def test_get_collection_config_default(self, mock_config_table):
        """Test default configuration when no config exists"""
        # Mock DynamoDB response with no item
        mock_config_table.get_item.return_value = {}
        
        config = get_collection_config()
        
        # Should return default values
        self.assertEqual(config['lookback_days'], 7)
        self.assertEqual(config['granularity'], 'DAILY')
        self.assertIn('BlendedCost', config['metrics'])
    
    @patch('lambda.data_collection.handler.ce_client')
    def test_collect_cost_explorer_data_success(self, mock_ce_client):
        """Test successful Cost Explorer data collection"""
        # Mock Cost Explorer response
        mock_response = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2024-01-01'},
                    'Groups': [
                        {
                            'Keys': ['Amazon EC2-Instance', 'us-east-1'],
                            'Metrics': {
                                'BlendedCost': {'Amount': '100.50', 'Unit': 'USD'},
                                'UsageQuantity': {'Amount': '744', 'Unit': 'Hrs'}
                            }
                        }
                    ]
                }
            ]
        }
        
        mock_ce_client.get_cost_and_usage.return_value = mock_response
        
        config = {'lookback_days': 7, 'granularity': 'DAILY', 'metrics': ['BlendedCost']}
        cost_data = collect_cost_explorer_data(config)
        
        self.assertEqual(len(cost_data), 1)
        self.assertEqual(cost_data[0]['service_name'], 'Amazon EC2-Instance')
        self.assertEqual(cost_data[0]['region'], 'us-east-1')
        self.assertEqual(float(cost_data[0]['cost_amount']), 100.50)
    
    @patch('lambda.data_collection.handler.ce_client')
    def test_collect_cost_explorer_data_error(self, mock_ce_client):
        """Test Cost Explorer data collection error handling"""
        # Mock Cost Explorer error
        mock_ce_client.get_cost_and_usage.side_effect = Exception("API Error")
        
        config = {'lookback_days': 7, 'granularity': 'DAILY', 'metrics': ['BlendedCost']}
        cost_data = collect_cost_explorer_data(config)
        
        # Should return empty list on error
        self.assertEqual(len(cost_data), 0)
    
    @patch('lambda.data_collection.handler.cloudwatch_client')
    def test_collect_cloudwatch_metrics_success(self, mock_cloudwatch_client):
        """Test successful CloudWatch metrics collection"""
        # Mock CloudWatch response
        mock_response = {
            'Datapoints': [
                {
                    'Timestamp': datetime.utcnow(),
                    'Average': 75.5,
                    'Unit': 'Percent'
                }
            ]
        }
        
        mock_cloudwatch_client.get_metric_statistics.return_value = mock_response
        
        config = {'cloudwatch_hours': 24}
        usage_data = collect_cloudwatch_metrics(config)
        
        # Should have collected some metrics
        self.assertGreater(len(usage_data), 0)
        
        # Verify data structure
        if usage_data:
            metric = usage_data[0]
            self.assertIn('service_id', metric)
            self.assertIn('timestamp', metric)
            self.assertIn('value', metric)
    
    @patch('lambda.data_collection.handler.cost_data_table')
    def test_store_cost_data_success(self, mock_table):
        """Test successful cost data storage"""
        # Mock batch writer
        mock_batch = MagicMock()
        mock_table.batch_writer.return_value.__enter__.return_value = mock_batch
        
        cost_data = [
            {
                'service_id': 'EC2#us-east-1',
                'timestamp': '2024-01-01',
                'cost_amount': Decimal('100.50')
            }
        ]
        
        # Should not raise exception
        store_cost_data(cost_data)
        
        # Verify batch writer was called
        mock_table.batch_writer.assert_called_once()
    
    @patch('lambda.data_collection.handler.cost_data_table')
    def test_store_cost_data_empty(self, mock_table):
        """Test storing empty cost data"""
        # Should handle empty data gracefully
        store_cost_data([])
        
        # Should not call batch writer for empty data
        mock_table.batch_writer.assert_not_called()
    
    def test_data_validation(self):
        """Test data validation functions"""
        from lambda.data_collection.utils import validate_cost_data
        
        # Valid record
        valid_record = {
            'service_id': 'EC2#us-east-1',
            'timestamp': '2024-01-01T00:00:00Z',
            'cost_amount': Decimal('100.50')
        }
        
        # Should not raise exception
        self.assertTrue(validate_cost_data(valid_record))
        
        # Invalid record - missing required field
        invalid_record = {
            'service_id': 'EC2#us-east-1',
            'cost_amount': Decimal('100.50')
            # Missing timestamp
        }
        
        with self.assertRaises(ValueError):
            validate_cost_data(invalid_record)
        
        # Invalid record - negative cost
        negative_cost_record = {
            'service_id': 'EC2#us-east-1',
            'timestamp': '2024-01-01T00:00:00Z',
            'cost_amount': Decimal('-10.00')
        }
        
        # Should still validate but log warning
        self.assertTrue(validate_cost_data(negative_cost_record))
    
    def test_date_range_calculation(self):
        """Test date range calculation utilities"""
        from lambda.data_collection.utils import calculate_date_ranges
        
        # Test daily ranges
        daily_ranges = calculate_date_ranges(3, 'DAILY')
        self.assertEqual(len(daily_ranges), 3)
        
        # Verify date format
        for date_range in daily_ranges:
            self.assertIn('Start', date_range)
            self.assertIn('End', date_range)
            
            # Verify date format
            start_date = datetime.strptime(date_range['Start'], '%Y-%m-%d')
            end_date = datetime.strptime(date_range['End'], '%Y-%m-%d')
            
            # End should be one day after start
            self.assertEqual((end_date - start_date).days, 1)
    
    def test_aws_services_list(self):
        """Test AWS services list utility"""
        from lambda.data_collection.utils import get_aws_services_list
        
        services = get_aws_services_list()
        
        # Should return a list
        self.assertIsInstance(services, list)
        self.assertGreater(len(services), 0)
        
        # Should contain common services
        service_names = ' '.join(services)
        self.assertIn('Compute', service_names)
        self.assertIn('Storage', service_names)
        self.assertIn('Lambda', service_names)
    
    def test_cost_record_formatting(self):
        """Test cost record formatting"""
        from lambda.data_collection.utils import format_cost_record
        
        service = 'Amazon EC2'
        region = 'us-east-1'
        time_period = '2024-01-01'
        metrics = {
            'BlendedCost': {'Amount': '100.50', 'Unit': 'USD'},
            'UsageQuantity': {'Amount': '744', 'Unit': 'Hrs'}
        }
        
        record = format_cost_record(service, region, time_period, metrics)
        
        # Verify record structure
        self.assertEqual(record['service_id'], f"{service}#{region}")
        self.assertEqual(record['service_name'], service)
        self.assertEqual(record['region'], region)
        self.assertEqual(record['timestamp'], time_period)
        self.assertEqual(float(record['cost_amount']), 100.50)
        self.assertEqual(float(record['usage_quantity']), 744)
        self.assertEqual(record['currency'], 'USD')
        
        # Verify TTL is set
        self.assertIn('ttl', record)
        self.assertIsInstance(record['ttl'], int)
    
    def test_usage_record_formatting(self):
        """Test usage record formatting"""
        from lambda.data_collection.utils import format_usage_record
        
        namespace = 'AWS/EC2'
        metric_name = 'CPUUtilization'
        datapoint = {
            'Timestamp': datetime.utcnow(),
            'Average': 75.5,
            'Unit': 'Percent'
        }
        
        record = format_usage_record(namespace, metric_name, datapoint)
        
        # Verify record structure
        self.assertEqual(record['service_id'], f"{namespace}#{metric_name}")
        self.assertEqual(record['namespace'], namespace)
        self.assertEqual(record['metric_name'], metric_name)
        self.assertEqual(float(record['value']), 75.5)
        self.assertEqual(record['unit'], 'Percent')
        
        # Verify timestamp format
        self.assertIn('timestamp', record)
        self.assertIn('T', record['timestamp'])  # ISO format
    
    def tearDown(self):
        """Clean up after each test"""
        # Clear environment variables
        for key in ['COST_DATA_TABLE', 'CONFIG_TABLE']:
            if key in os.environ:
                del os.environ[key]


if __name__ == '__main__':
    unittest.main(verbosity=2)
