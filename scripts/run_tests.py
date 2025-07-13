"""
Test runner for Cost Optimization Dashboard
"""

import unittest
import sys
import os
import time
import boto3
from datetime import datetime
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestRunner:
    """Test runner for the Cost Optimization Dashboard"""
    
    def __init__(self):
        self.test_results = {
            'unit_tests': {},
            'integration_tests': {},
            'validation_tests': {},
            'performance_tests': {}
        }
        
        # AWS clients for validation
        self.dynamodb = boto3.resource('dynamodb')
        self.lambda_client = boto3.client('lambda')
        self.sns = boto3.client('sns')
        self.quicksight = boto3.client('quicksight')
    
    def run_unit_tests(self):
        """Run unit tests"""
        logger.info("Running unit tests...")
        
        # Discover and run unit tests
        test_loader = unittest.TestLoader()
        test_suite = test_loader.discover('../tests/unit', pattern='test_*.py')
        
        # Run tests
        test_runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        result = test_runner.run(test_suite)
        
        self.test_results['unit_tests'] = {
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'success': result.wasSuccessful()
        }
        
        logger.info(f"Unit tests completed: {result.testsRun} tests, "
                   f"{len(result.failures)} failures, {len(result.errors)} errors")
        
        return result.wasSuccessful()
    
    def run_integration_tests(self):
        """Run integration tests"""
        logger.info("Running integration tests...")
        
        # Check if test environment is available
        if not self.check_test_environment():
            logger.warning("Test environment not available, skipping integration tests")
            return False
        
        # Discover and run integration tests
        test_loader = unittest.TestLoader()
        test_suite = test_loader.discover('../tests/integration', pattern='test_*.py')
        
        # Run tests
        test_runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        result = test_runner.run(test_suite)
        
        self.test_results['integration_tests'] = {
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'success': result.wasSuccessful()
        }
        
        logger.info(f"Integration tests completed: {result.testsRun} tests, "
                   f"{len(result.failures)} failures, {len(result.errors)} errors")
        
        return result.wasSuccessful()
    
    def check_test_environment(self):
        """Check if test environment is properly set up"""
        logger.info("Checking test environment...")
        
        try:
            # Check if test tables exist
            test_tables = [
                'cost-data-test',
                'cost-analysis-test',
                'cost-config-test',
                'cost-alerts-test'
            ]
            
            for table_name in test_tables:
                try:
                    table = self.dynamodb.Table(table_name)
                    table.load()
                    logger.info(f"Test table {table_name} is available")
                except Exception as e:
                    logger.warning(f"Test table {table_name} not available: {str(e)}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking test environment: {str(e)}")
            return False
    
    def run_validation_tests(self):
        """Run validation tests for deployed infrastructure"""
        logger.info("Running validation tests...")
        
        validation_results = {
            'lambda_functions': self.validate_lambda_functions(),
            'dynamodb_tables': self.validate_dynamodb_tables(),
            'sns_topics': self.validate_sns_topics(),
            'quicksight_resources': self.validate_quicksight_resources()
        }
        
        success = all(validation_results.values())
        
        self.test_results['validation_tests'] = {
            'components_validated': len(validation_results),
            'successful_validations': sum(validation_results.values()),
            'success': success,
            'details': validation_results
        }
        
        logger.info(f"Validation tests completed: {success}")
        return success
    
    def validate_lambda_functions(self):
        """Validate Lambda functions are deployed and configured correctly"""
        logger.info("Validating Lambda functions...")
        
        expected_functions = [
            'cost-data-collection',
            'cost-data-processing',
            'cost-alerting'
        ]
        
        try:
            for function_name in expected_functions:
                try:
                    response = self.lambda_client.get_function(FunctionName=function_name)
                    logger.info(f"Lambda function {function_name} is deployed")
                    
                    # Check function configuration
                    config = response['Configuration']
                    if config['Runtime'] != 'python3.9':
                        logger.warning(f"Function {function_name} has unexpected runtime: {config['Runtime']}")
                    
                    if config['State'] != 'Active':
                        logger.warning(f"Function {function_name} is not active: {config['State']}")
                        return False
                        
                except self.lambda_client.exceptions.ResourceNotFoundException:
                    logger.error(f"Lambda function {function_name} not found")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating Lambda functions: {str(e)}")
            return False
    
    def validate_dynamodb_tables(self):
        """Validate DynamoDB tables are created and configured correctly"""
        logger.info("Validating DynamoDB tables...")
        
        expected_tables = [
            'cost-data',
            'cost-analysis',
            'cost-config',
            'cost-alerts',
            'cost-recommendations'
        ]
        
        try:
            for table_name in expected_tables:
                try:
                    table = self.dynamodb.Table(table_name)
                    table.load()
                    
                    logger.info(f"DynamoDB table {table_name} is available")
                    
                    # Check table status
                    if table.table_status != 'ACTIVE':
                        logger.warning(f"Table {table_name} is not active: {table.table_status}")
                        return False
                    
                    # Check billing mode
                    if table.billing_mode_summary['BillingMode'] != 'PAY_PER_REQUEST':
                        logger.warning(f"Table {table_name} is not using on-demand billing")
                    
                except Exception as e:
                    logger.error(f"DynamoDB table {table_name} validation failed: {str(e)}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating DynamoDB tables: {str(e)}")
            return False
    
    def validate_sns_topics(self):
        """Validate SNS topics are created"""
        logger.info("Validating SNS topics...")
        
        expected_topics = [
            'cost-alerts',
            'cost-anomalies',
            'cost-reports',
            'budget-alerts',
            'cost-optimization'
        ]
        
        try:
            # List all topics
            response = self.sns.list_topics()
            topic_arns = [topic['TopicArn'] for topic in response['Topics']]
            
            for topic_name in expected_topics:
                # Check if topic exists
                topic_found = any(topic_name in arn for arn in topic_arns)
                
                if topic_found:
                    logger.info(f"SNS topic {topic_name} is available")
                else:
                    logger.warning(f"SNS topic {topic_name} not found")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating SNS topics: {str(e)}")
            return False
    
    def validate_quicksight_resources(self):
        """Validate QuickSight resources are created"""
        logger.info("Validating QuickSight resources...")
        
        try:
            # Get AWS account ID
            sts = boto3.client('sts')
            account_id = sts.get_caller_identity()['Account']
            
            # Check datasets
            expected_datasets = [
                'cost-data-dataset',
                'cost-analysis-dataset'
            ]
            
            for dataset_id in expected_datasets:
                try:
                    response = self.quicksight.describe_data_set(
                        AwsAccountId=account_id,
                        DataSetId=dataset_id
                    )
                    logger.info(f"QuickSight dataset {dataset_id} is available")
                except Exception as e:
                    logger.warning(f"QuickSight dataset {dataset_id} not found: {str(e)}")
                    return False
            
            # Check dashboards
            expected_dashboards = [
                'cost-optimization-executive-dashboard',
                'cost-optimization-service-analysis'
            ]
            
            for dashboard_id in expected_dashboards:
                try:
                    response = self.quicksight.describe_dashboard(
                        AwsAccountId=account_id,
                        DashboardId=dashboard_id
                    )
                    logger.info(f"QuickSight dashboard {dashboard_id} is available")
                except Exception as e:
                    logger.warning(f"QuickSight dashboard {dashboard_id} not found: {str(e)}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating QuickSight resources: {str(e)}")
            return False
    
    def run_performance_tests(self):
        """Run performance tests"""
        logger.info("Running performance tests...")
        
        performance_results = {
            'lambda_cold_start': self.test_lambda_cold_start(),
            'dynamodb_query_performance': self.test_dynamodb_performance(),
            'end_to_end_latency': self.test_end_to_end_latency()
        }
        
        success = all(result['success'] for result in performance_results.values())
        
        self.test_results['performance_tests'] = {
            'tests_run': len(performance_results),
            'success': success,
            'details': performance_results
        }
        
        logger.info(f"Performance tests completed: {success}")
        return success
    
    def test_lambda_cold_start(self):
        """Test Lambda function cold start performance"""
        logger.info("Testing Lambda cold start performance...")
        
        try:
            function_name = 'cost-data-collection'
            
            start_time = time.time()
            
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps({'test': True})
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Cold start should be under 10 seconds
            success = duration < 10.0
            
            logger.info(f"Lambda cold start took {duration:.2f} seconds")
            
            return {
                'success': success,
                'duration_seconds': duration,
                'threshold_seconds': 10.0
            }
            
        except Exception as e:
            logger.error(f"Error testing Lambda cold start: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def test_dynamodb_performance(self):
        """Test DynamoDB query performance"""
        logger.info("Testing DynamoDB query performance...")
        
        try:
            table = self.dynamodb.Table('cost-data')
            
            start_time = time.time()
            
            # Perform a sample query
            response = table.scan(Limit=100)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Query should complete under 2 seconds
            success = duration < 2.0
            
            logger.info(f"DynamoDB query took {duration:.2f} seconds")
            
            return {
                'success': success,
                'duration_seconds': duration,
                'threshold_seconds': 2.0,
                'items_returned': len(response.get('Items', []))
            }
            
        except Exception as e:
            logger.error(f"Error testing DynamoDB performance: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def test_end_to_end_latency(self):
        """Test end-to-end workflow latency"""
        logger.info("Testing end-to-end workflow latency...")
        
        try:
            start_time = time.time()
            
            # Simulate end-to-end workflow
            # 1. Data collection (simulated)
            # 2. Data processing
            # 3. Alerting
            
            # For now, just test data processing
            response = self.lambda_client.invoke(
                FunctionName='cost-data-processing',
                InvocationType='RequestResponse',
                Payload=json.dumps({'test': True})
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # End-to-end should complete under 30 seconds
            success = duration < 30.0
            
            logger.info(f"End-to-end workflow took {duration:.2f} seconds")
            
            return {
                'success': success,
                'duration_seconds': duration,
                'threshold_seconds': 30.0
            }
            
        except Exception as e:
            logger.error(f"Error testing end-to-end latency: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("Generating test report...")
        
        report = {
            'test_run_timestamp': datetime.utcnow().isoformat(),
            'overall_success': all(
                result.get('success', False) 
                for result in self.test_results.values()
            ),
            'test_results': self.test_results,
            'summary': {
                'total_test_categories': len(self.test_results),
                'successful_categories': sum(
                    1 for result in self.test_results.values() 
                    if result.get('success', False)
                )
            }
        }
        
        # Save report to file
        report_filename = f"test_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Test report saved to {report_filename}")
        
        # Print summary
        print("\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        print(f"Overall Success: {report['overall_success']}")
        print(f"Test Categories: {report['summary']['successful_categories']}/{report['summary']['total_test_categories']}")
        
        for category, results in self.test_results.items():
            status = "✓" if results.get('success', False) else "✗"
            print(f"{status} {category.replace('_', ' ').title()}")
        
        print("="*50)
        
        return report
    
    def run_all_tests(self):
        """Run all test categories"""
        logger.info("Starting comprehensive test suite...")
        
        # Run tests in order
        self.run_unit_tests()
        self.run_integration_tests()
        self.run_validation_tests()
        self.run_performance_tests()
        
        # Generate report
        report = self.generate_test_report()
        
        return report['overall_success']


def main():
    """Main test runner function"""
    test_runner = TestRunner()
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        
        if test_type == 'unit':
            success = test_runner.run_unit_tests()
        elif test_type == 'integration':
            success = test_runner.run_integration_tests()
        elif test_type == 'validation':
            success = test_runner.run_validation_tests()
        elif test_type == 'performance':
            success = test_runner.run_performance_tests()
        else:
            print(f"Unknown test type: {test_type}")
            print("Available types: unit, integration, validation, performance")
            sys.exit(1)
    else:
        # Run all tests
        success = test_runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
