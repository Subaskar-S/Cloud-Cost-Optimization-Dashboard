# Deployment Guide

This guide walks you through deploying the AWS Cloud Cost Optimization Dashboard from scratch.

## Prerequisites

### Required Tools
- **AWS CLI** (v2.0+) - [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- **AWS CDK** (v2.0+) - `npm install -g aws-cdk`
- **Python** (3.9+) - [Download](https://www.python.org/downloads/)
- **Node.js** (16+) - [Download](https://nodejs.org/)
- **Git** - [Installation Guide](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)

### AWS Account Setup
1. **AWS Account** with administrative access
2. **Cost Explorer** enabled in your AWS account
3. **QuickSight** subscription (Standard or Enterprise)
4. **Billing alerts** enabled in CloudWatch

### Required AWS Permissions
Your AWS user/role needs the following permissions:
- `PowerUserAccess` or equivalent
- `QuickSightFullAccess`
- `CostExplorerServiceRolePolicy`
- Custom policy for Cost Explorer API access

## Step 1: Initial Setup

### 1.1 Clone and Configure
```bash
git clone <repository-url>
cd cloud-cost-optimization-dashboard

# Install Python dependencies
pip install -r requirements.txt

# Install CDK dependencies
cd infrastructure
npm install
```

### 1.2 Configure AWS CLI
```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, Region, and Output format
```

### 1.3 Bootstrap CDK (First time only)
```bash
cdk bootstrap
```

## Step 2: Configuration

### 2.1 Update Configuration Files
Edit the configuration files in the `config/` directory:

**config/thresholds.json**
- Set appropriate cost thresholds for your organization
- Configure notification settings
- Update email addresses and Slack webhook URLs

**config/budgets.json**
- Set monthly/quarterly/annual budget limits
- Configure service-specific budgets
- Set up team and project budgets

### 2.2 Environment Variables
Create a `.env` file in the root directory:
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Notification Settings
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
NOTIFICATION_EMAIL=alerts@yourcompany.com

# QuickSight Configuration
QUICKSIGHT_USER=your-quicksight-user
QUICKSIGHT_NAMESPACE=default

# Optional: Custom Settings
COST_COLLECTION_SCHEDULE=rate(1 hour)
ANALYSIS_SCHEDULE=rate(6 hours)
ALERT_SCHEDULE=rate(15 minutes)
```

## Step 3: Deploy Infrastructure

### 3.1 Deploy Core Infrastructure
```bash
cd infrastructure

# Deploy DynamoDB tables
cdk deploy CostOptimizationStack-DynamoDB

# Deploy Lambda functions
cdk deploy CostOptimizationStack-Lambda

# Deploy CloudWatch Events and SNS
cdk deploy CostOptimizationStack-Events
```

### 3.2 Verify Deployment
```bash
# Check DynamoDB tables
aws dynamodb list-tables --query 'TableNames[?contains(@, `cost`)]'

# Check Lambda functions
aws lambda list-functions --query 'Functions[?contains(FunctionName, `cost`)]'

# Check CloudWatch Events
aws events list-rules --query 'Rules[?contains(Name, `cost`)]'
```

## Step 4: Configure QuickSight

### 4.1 Set Up Data Sources
1. **Log into QuickSight Console**
   - Go to https://quicksight.aws.amazon.com/
   - Select your region

2. **Create Data Source**
   ```bash
   # Create S3 bucket for QuickSight data
   aws s3 mb s3://your-cost-dashboard-data-bucket
   
   # Set up DynamoDB to S3 export (automated via Lambda)
   ```

3. **Configure DynamoDB Connection**
   - In QuickSight, go to "Manage data"
   - Click "New data set"
   - Select "DynamoDB" as data source
   - Configure connection to `cost-data` table

### 4.2 Create Datasets
Create the following datasets in QuickSight:

**Cost Data Dataset**
- Source: DynamoDB `cost-data` table
- Refresh: Daily at 6 AM UTC
- Filters: Last 90 days of data

**Analysis Dataset**
- Source: DynamoDB `cost-analysis` table
- Refresh: Every 6 hours
- Aggregations: Pre-calculated summaries

### 4.3 Build Dashboards
Import dashboard templates from `visualization/dashboards/`:

```bash
# Upload dashboard definitions
aws quicksight create-dashboard --cli-input-json file://visualization/dashboards/executive-dashboard.json
aws quicksight create-dashboard --cli-input-json file://visualization/dashboards/service-analysis.json
aws quicksight create-dashboard --cli-input-json file://visualization/dashboards/optimization-dashboard.json
```

## Step 5: Configure Notifications

### 5.1 Set Up SNS Topics
```bash
# Create SNS topics (done automatically by CDK)
aws sns list-topics --query 'Topics[?contains(TopicArn, `cost`)]'
```

### 5.2 Configure Email Subscriptions
```bash
# Subscribe to cost alerts
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:cost-alerts \
  --protocol email \
  --notification-endpoint your-email@company.com
```

### 5.3 Set Up Slack Integration
1. Create a Slack app in your workspace
2. Add incoming webhook
3. Update `SLACK_WEBHOOK_URL` in your `.env` file
4. Redeploy the alerting Lambda function

## Step 6: Testing and Validation

### 6.1 Test Data Collection
```bash
# Manually trigger data collection
aws lambda invoke \
  --function-name cost-data-collection \
  --payload '{}' \
  response.json

# Check results
cat response.json
```

### 6.2 Test Analysis Pipeline
```bash
# Trigger cost analysis
aws lambda invoke \
  --function-name cost-analysis-processor \
  --payload '{}' \
  response.json
```

### 6.3 Test Alerting
```bash
# Trigger alert check
aws lambda invoke \
  --function-name cost-alerting \
  --payload '{"test_mode": true}' \
  response.json
```

### 6.4 Validate QuickSight Dashboards
1. Open QuickSight console
2. Navigate to your dashboards
3. Verify data is loading correctly
4. Test filters and drill-down functionality

## Step 7: Monitoring and Maintenance

### 7.1 Set Up CloudWatch Monitoring
```bash
# Create custom CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name "Cost-Optimization-System" \
  --dashboard-body file://monitoring/cloudwatch-dashboard.json
```

### 7.2 Configure Log Retention
```bash
# Set log retention for Lambda functions
aws logs put-retention-policy \
  --log-group-name /aws/lambda/cost-data-collection \
  --retention-in-days 30
```

### 7.3 Schedule Regular Maintenance
- **Weekly**: Review and update cost thresholds
- **Monthly**: Analyze optimization recommendations
- **Quarterly**: Review and adjust budgets

## Troubleshooting

### Common Issues

**1. Cost Explorer API Access Denied**
```bash
# Ensure Cost Explorer is enabled
aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-01-02 --granularity DAILY --metrics BlendedCost
```

**2. QuickSight Connection Issues**
- Verify QuickSight has permissions to access DynamoDB
- Check VPC configuration if using private subnets
- Ensure data source refresh is configured correctly

**3. Lambda Function Timeouts**
- Increase memory allocation for data processing functions
- Optimize DynamoDB queries with proper indexing
- Consider breaking large operations into smaller chunks

**4. Missing Cost Data**
- Verify CloudWatch Events are triggering Lambda functions
- Check Lambda function logs for errors
- Ensure Cost Explorer API quotas are not exceeded

### Debugging Commands
```bash
# Check Lambda function logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/cost"

# View recent log events
aws logs filter-log-events \
  --log-group-name "/aws/lambda/cost-data-collection" \
  --start-time $(date -d "1 hour ago" +%s)000

# Check DynamoDB table status
aws dynamodb describe-table --table-name cost-data

# Verify SNS topic subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:123456789012:cost-alerts
```

## Security Considerations

### 1. IAM Roles and Policies
- Use least privilege principle
- Regularly review and audit permissions
- Enable CloudTrail for API logging

### 2. Data Encryption
- Enable encryption at rest for DynamoDB
- Use HTTPS for all API communications
- Encrypt SNS messages

### 3. Network Security
- Deploy Lambda functions in private subnets (optional)
- Use VPC endpoints for AWS service access
- Implement proper security groups

## Cost Optimization

### 1. Lambda Optimization
- Right-size memory allocation
- Use provisioned concurrency only when needed
- Optimize cold start performance

### 2. DynamoDB Optimization
- Use on-demand billing for variable workloads
- Implement TTL for historical data cleanup
- Optimize partition key distribution

### 3. QuickSight Optimization
- Use SPICE for better performance
- Schedule data refreshes during off-peak hours
- Monitor SPICE capacity usage

## Next Steps

After successful deployment:

1. **Customize Dashboards**: Tailor QuickSight dashboards to your organization's needs
2. **Set Up Automation**: Configure automated responses to cost alerts
3. **Integrate with ITSM**: Connect alerts to your ticketing system
4. **Expand Monitoring**: Add more AWS services to cost tracking
5. **Implement Governance**: Set up cost allocation and chargeback processes

For additional support, refer to the [User Guide](user_guide.md) and [API Reference](api_reference.md).
