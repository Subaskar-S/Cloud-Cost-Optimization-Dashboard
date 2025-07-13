"""
Unit tests for alerting Lambda function
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add lambda directory to path
sys.path.append('../../lambda/alerting')

from lambda.alerting.handler import (
    get_alerting_config,
    check_threshold_alerts,
    check_cost_anomalies,
    create_alert,
    is_duplicate_alert,
    send_alert_notification
)


class TestAlerting(unittest.TestCase):
    """Unit tests for alerting functions"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock environment variables
        os.environ['COST_DATA_TABLE'] = 'test-cost-data'
        os.environ['CONFIG_TABLE'] = 'test-config'
        os.environ['ALERTS_TABLE'] = 'test-alerts'
        os.environ['ALERTS_TOPIC_ARN'] = 'arn:aws:sns:us-east-1:123456789012:test-alerts'
        
        # Mock AWS clients
        self.mock_dynamodb = Mock()
        self.mock_sns = Mock()
    
    @patch('lambda.alerting.handler.config_table')
    def test_get_alerting_config_success(self, mock_config_table):
        """Test successful alerting configuration retrieval"""
        # Mock DynamoDB response
        mock_config_table.get_item.return_value = {
            'Item': {
                'cost_thresholds': {
                    'daily': {'warning': 100, 'critical': 200}
                },
                'service_thresholds': {
                    'EC2': {'daily': 50}
                },
                'anomaly_detection': {
                    'enabled': True,
                    'sensitivity': 'medium'
                }
            }
        }
        
        config = get_alerting_config()
        
        self.assertEqual(config['cost_thresholds']['daily']['warning'], 100)
        self.assertEqual(config['service_thresholds']['EC2']['daily'], 50)
        self.assertTrue(config['anomaly_detection']['enabled'])
    
    @patch('lambda.alerting.handler.config_table')
    def test_get_alerting_config_default(self, mock_config_table):
        """Test default configuration when no config exists"""
        # Mock DynamoDB response with no item
        mock_config_table.get_item.return_value = {}
        
        config = get_alerting_config()
        
        # Should return default values
        self.assertIn('cost_thresholds', config)
        self.assertIn('daily', config['cost_thresholds'])
    
    @patch('lambda.alerting.handler.get_daily_costs')
    def test_check_threshold_alerts_breach(self, mock_get_daily_costs):
        """Test threshold alert generation when thresholds are breached"""
        # Mock cost data that exceeds thresholds
        mock_get_daily_costs.return_value = [
            {
                'service_name': 'Amazon EC2',
                'cost_amount': Decimal('150')  # Above threshold
            },
            {
                'service_name': 'Amazon S3',
                'cost_amount': Decimal('25')
            }
        ]
        
        config = {
            'cost_thresholds': {
                'daily': {'warning': 100, 'critical': 200}
            },
            'service_thresholds': {
                'Amazon EC2': {'daily': 50}
            }
        }
        
        alerts = check_threshold_alerts(config, test_mode=True)
        
        # Should generate alerts for both overall and service thresholds
        self.assertGreater(len(alerts), 0)
        
        # Check alert content
        alert_messages = [alert['message'] for alert in alerts]
        self.assertTrue(any('exceeded' in msg for msg in alert_messages))
    
    @patch('lambda.alerting.handler.get_daily_costs')
    def test_check_threshold_alerts_no_breach(self, mock_get_daily_costs):
        """Test no alerts when thresholds are not breached"""
        # Mock cost data below thresholds
        mock_get_daily_costs.return_value = [
            {
                'service_name': 'Amazon EC2',
                'cost_amount': Decimal('25')  # Below threshold
            }
        ]
        
        config = {
            'cost_thresholds': {
                'daily': {'warning': 100, 'critical': 200}
            },
            'service_thresholds': {
                'Amazon EC2': {'daily': 50}
            }
        }
        
        alerts = check_threshold_alerts(config, test_mode=True)
        
        # Should not generate any alerts
        self.assertEqual(len(alerts), 0)
    
    @patch('lambda.alerting.handler.get_cost_data_range')
    @patch('lambda.alerting.handler.detect_service_anomalies')
    def test_check_cost_anomalies_detected(self, mock_detect_anomalies, mock_get_cost_data):
        """Test anomaly detection when anomalies are found"""
        # Mock cost data
        mock_get_cost_data.return_value = [
            {
                'service_name': 'Amazon EC2',
                'timestamp': '2024-01-01',
                'cost_amount': Decimal('100')
            }
        ]
        
        # Mock detected anomalies
        mock_detect_anomalies.return_value = [
            {
                'service': 'Amazon EC2',
                'current_cost': Decimal('150'),
                'expected_cost': Decimal('100'),
                'severity': 'warning',
                'description': 'Cost spike detected'
            }
        ]
        
        config = {
            'anomaly_detection': {
                'enabled': True,
                'sensitivity': 'medium'
            }
        }
        
        alerts = check_cost_anomalies(config, test_mode=True)
        
        # Should generate anomaly alerts
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['alert_type'], 'anomaly_detection')
        self.assertEqual(alerts[0]['service'], 'Amazon EC2')
    
    @patch('lambda.alerting.handler.get_cost_data_range')
    def test_check_cost_anomalies_disabled(self, mock_get_cost_data):
        """Test no anomaly detection when disabled"""
        config = {
            'anomaly_detection': {
                'enabled': False
            }
        }
        
        alerts = check_cost_anomalies(config, test_mode=True)
        
        # Should not generate any alerts when disabled
        self.assertEqual(len(alerts), 0)
    
    def test_create_alert_structure(self):
        """Test alert creation with proper structure"""
        alert = create_alert(
            alert_type='threshold_breach',
            severity='warning',
            service='Amazon EC2',
            region='us-east-1',
            current_cost=150.0,
            threshold=100.0,
            message='Cost exceeded threshold',
            test_mode=True
        )
        
        # Verify alert structure
        self.assertEqual(alert['alert_type'], 'threshold_breach')
        self.assertEqual(alert['severity'], 'warning')
        self.assertEqual(alert['service'], 'Amazon EC2')
        self.assertEqual(alert['region'], 'us-east-1')
        self.assertEqual(float(alert['current_cost']), 150.0)
        self.assertEqual(float(alert['threshold']), 100.0)
        self.assertEqual(alert['message'], 'Cost exceeded threshold')
        self.assertTrue(alert['test_mode'])
        self.assertEqual(alert['status'], 'active')
        self.assertFalse(alert['acknowledged'])
        self.assertFalse(alert['resolved'])
        
        # Verify required fields
        self.assertIn('alert_id', alert)
        self.assertIn('timestamp', alert)
        self.assertIn('ttl', alert)
    
    @patch('lambda.alerting.handler.alerts_table')
    def test_is_duplicate_alert_found(self, mock_alerts_table):
        """Test duplicate alert detection when duplicate exists"""
        # Mock existing alert
        mock_alerts_table.scan.return_value = {
            'Items': [
                {
                    'alert_id': 'existing-alert',
                    'alert_type': 'threshold_breach',
                    'service': 'Amazon EC2',
                    'status': 'active'
                }
            ]
        }
        
        alert = {
            'alert_type': 'threshold_breach',
            'service': 'Amazon EC2',
            'region': 'us-east-1'
        }
        
        is_duplicate = is_duplicate_alert(alert)
        self.assertTrue(is_duplicate)
    
    @patch('lambda.alerting.handler.alerts_table')
    def test_is_duplicate_alert_not_found(self, mock_alerts_table):
        """Test duplicate alert detection when no duplicate exists"""
        # Mock no existing alerts
        mock_alerts_table.scan.return_value = {'Items': []}
        
        alert = {
            'alert_type': 'threshold_breach',
            'service': 'Amazon EC2',
            'region': 'us-east-1'
        }
        
        is_duplicate = is_duplicate_alert(alert)
        self.assertFalse(is_duplicate)
    
    @patch('lambda.alerting.handler.sns')
    @patch('lambda.alerting.handler.alerts_table')
    def test_send_alert_notification_success(self, mock_alerts_table, mock_sns):
        """Test successful alert notification sending"""
        # Mock SNS publish success
        mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
        
        alert = {
            'alert_id': 'test-alert',
            'timestamp': datetime.utcnow().isoformat(),
            'alert_type': 'threshold_breach',
            'severity': 'warning',
            'service': 'Amazon EC2',
            'region': 'us-east-1',
            'current_cost': Decimal('150'),
            'threshold': Decimal('100'),
            'message': 'Test alert message'
        }
        
        # Should not raise exception
        send_alert_notification(alert)
        
        # Verify SNS publish was called
        mock_sns.publish.assert_called_once()
        
        # Verify alert table update was called
        mock_alerts_table.update_item.assert_called_once()
    
    def test_alert_message_formatting(self):
        """Test alert message formatting"""
        from lambda.alerting.handler import format_alert_message, format_alert_subject
        
        alert = {
            'alert_id': 'test-alert',
            'alert_type': 'threshold_breach',
            'severity': 'warning',
            'service': 'Amazon EC2',
            'region': 'us-east-1',
            'current_cost': Decimal('150'),
            'threshold': Decimal('100'),
            'message': 'Test alert message',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Test message formatting
        message = format_alert_message(alert)
        
        self.assertIn('alert_id', message)
        self.assertIn('service', message)
        self.assertIn('current_cost', message)
        self.assertIn('dashboard_link', message)
        self.assertIn('actions', message)
        
        # Test subject formatting
        subject = format_alert_subject(alert)
        
        self.assertIn('Cost Alert', subject)
        self.assertIn('Amazon EC2', subject)
        self.assertIn('WARNING', subject)
        self.assertIn('⚠️', subject)  # Warning emoji
    
    def test_anomaly_detection_algorithm(self):
        """Test anomaly detection algorithm"""
        from lambda.alerting.handler import detect_service_anomalies
        
        # Create test data with clear anomaly
        cost_data = []
        
        # Normal costs for 10 days
        for i in range(10):
            cost_data.append({
                'service_name': 'Amazon EC2',
                'timestamp': f'2024-01-{i+1:02d}',
                'cost_amount': Decimal('100')  # Consistent cost
            })
        
        # Add anomaly
        cost_data.append({
            'service_name': 'Amazon EC2',
            'timestamp': '2024-01-11',
            'cost_amount': Decimal('300')  # 3x normal cost
        })
        
        anomalies = detect_service_anomalies(cost_data, sensitivity='medium')
        
        # Should detect the anomaly
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]['service'], 'Amazon EC2')
        self.assertEqual(float(anomalies[0]['current_cost']), 300.0)
        self.assertIn('severity', anomalies[0])
    
    def test_topic_selection(self):
        """Test SNS topic selection for different alert types"""
        from lambda.alerting.handler import get_topic_for_alert
        
        # Test threshold breach alert
        threshold_alert = {'alert_type': 'threshold_breach'}
        topic = get_topic_for_alert(threshold_alert)
        self.assertEqual(topic, os.environ['ALERTS_TOPIC_ARN'])
        
        # Test anomaly detection alert
        anomaly_alert = {'alert_type': 'anomaly_detection'}
        topic = get_topic_for_alert(anomaly_alert)
        # Should use anomalies topic (if configured)
        self.assertIsNotNone(topic)
        
        # Test budget alert
        budget_alert = {'alert_type': 'budget_exceeded'}
        topic = get_topic_for_alert(budget_alert)
        # Should use budget topic (if configured)
        self.assertIsNotNone(topic)
    
    def tearDown(self):
        """Clean up after each test"""
        # Clear environment variables
        env_vars = [
            'COST_DATA_TABLE', 'CONFIG_TABLE', 'ALERTS_TABLE', 
            'ALERTS_TOPIC_ARN', 'ANOMALIES_TOPIC_ARN', 'BUDGET_TOPIC_ARN'
        ]
        
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]


if __name__ == '__main__':
    unittest.main(verbosity=2)
