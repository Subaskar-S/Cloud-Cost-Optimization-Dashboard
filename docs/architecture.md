# System Architecture

## Overview

The AWS Cloud Cost Optimization Dashboard is built using a serverless, event-driven architecture that provides real-time cost monitoring, analysis, and alerting capabilities.

## Architecture Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CloudWatch    │    │  Cost Explorer   │    │   CloudWatch    │
│     Events      │    │       API        │    │    Metrics      │
│   (Scheduler)   │    │                  │    │                 │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                      │                       │
          │                      │                       │
          ▼                      ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Lambda Functions                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │    Data     │  │    Data     │  │       Alerting          │ │
│  │ Collection  │  │ Processing  │  │    & Notification       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────┬───────────────┬─────────────────────┬─────────────────┘
          │               │                     │
          ▼               ▼                     ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    DynamoDB     │    │    DynamoDB     │    │       SNS       │
│   Cost Data     │    │   Analysis      │    │    Topics       │
│     Table       │    │     Table       │    │                 │
└─────────┬───────┘    └─────────────────┘    └─────────┬───────┘
          │                                             │
          ▼                                             ▼
┌─────────────────┐                            ┌─────────────────┐
│   QuickSight    │                            │  Email/Slack    │
│   Dashboard     │                            │   Notifications │
│                 │                            │                 │
└─────────────────┘                            └─────────────────┘
```

## Components

### 1. Data Collection Layer

#### CloudWatch Events (EventBridge)
- **Purpose**: Triggers Lambda functions on schedule
- **Schedule**: Configurable (hourly, daily, weekly)
- **Events**: 
  - Cost data collection trigger
  - Analysis job trigger
  - Report generation trigger

#### Cost Explorer API
- **Purpose**: Primary source for detailed cost and usage data
- **Data Retrieved**:
  - Daily/monthly costs by service
  - Usage metrics by resource
  - Cost by tags and dimensions
  - Forecasting data

#### CloudWatch Metrics
- **Purpose**: Real-time usage metrics
- **Metrics Collected**:
  - EC2 instance utilization
  - Lambda invocation counts
  - S3 storage usage
  - RDS connection metrics

### 2. Processing Layer

#### Lambda Functions

##### Data Collection Function (`collect_cost_data`)
- **Runtime**: Python 3.9
- **Memory**: 512 MB
- **Timeout**: 5 minutes
- **Responsibilities**:
  - Fetch cost data from Cost Explorer API
  - Retrieve CloudWatch metrics
  - Transform and normalize data
  - Store in DynamoDB

##### Data Processing Function (`process_cost_analysis`)
- **Runtime**: Python 3.9
- **Memory**: 1024 MB
- **Timeout**: 10 minutes
- **Responsibilities**:
  - Aggregate cost data by time periods
  - Calculate trends and anomalies
  - Generate optimization recommendations
  - Update analysis tables

##### Alerting Function (`cost_alerting`)
- **Runtime**: Python 3.9
- **Memory**: 256 MB
- **Timeout**: 2 minutes
- **Responsibilities**:
  - Monitor cost thresholds
  - Detect anomalies
  - Send notifications via SNS
  - Generate alert reports

### 3. Storage Layer

#### DynamoDB Tables

##### Cost Data Table (`cost-data`)
- **Partition Key**: `service_id` (String)
- **Sort Key**: `timestamp` (String, ISO format)
- **Attributes**:
  - `cost_amount` (Number)
  - `usage_quantity` (Number)
  - `region` (String)
  - `tags` (Map)
  - `resource_id` (String)
- **Indexes**:
  - GSI1: `region-timestamp-index`
  - GSI2: `tag-timestamp-index`

##### Analysis Data Table (`cost-analysis`)
- **Partition Key**: `analysis_type` (String)
- **Sort Key**: `period` (String)
- **Attributes**:
  - `total_cost` (Number)
  - `service_breakdown` (Map)
  - `trends` (Map)
  - `recommendations` (List)
  - `created_at` (String)

##### Configuration Table (`cost-config`)
- **Partition Key**: `config_type` (String)
- **Attributes**:
  - `thresholds` (Map)
  - `budgets` (Map)
  - `notification_settings` (Map)

### 4. Visualization Layer

#### Amazon QuickSight
- **Data Sources**: DynamoDB tables via S3 export
- **Dashboards**:
  - Executive Summary Dashboard
  - Service-wise Cost Analysis
  - Regional Cost Breakdown
  - Optimization Recommendations

#### Dashboard Components
- **Cost Overview**: Total spend, trends, forecasts
- **Service Analysis**: Top services by cost
- **Regional View**: Cost distribution by region
- **Tag Analysis**: Cost by project/team/environment
- **Alerts Summary**: Recent alerts and thresholds

### 5. Notification Layer

#### Amazon SNS
- **Topics**:
  - `cost-alerts`: Threshold breaches
  - `cost-anomalies`: Unusual spending patterns
  - `cost-reports`: Weekly/monthly summaries

#### Notification Channels
- **Email**: Direct email notifications
- **Slack**: Webhook integration for team channels
- **SMS**: Critical alerts only

## Data Flow

### 1. Collection Flow
```
CloudWatch Event → Lambda (collect_cost_data) → Cost Explorer API
                                              → CloudWatch Metrics
                                              → DynamoDB (cost-data)
```

### 2. Processing Flow
```
CloudWatch Event → Lambda (process_cost_analysis) → DynamoDB (cost-data)
                                                  → DynamoDB (cost-analysis)
```

### 3. Alerting Flow
```
CloudWatch Event → Lambda (cost_alerting) → DynamoDB (cost-analysis)
                                          → SNS Topics
                                          → Email/Slack
```

### 4. Visualization Flow
```
DynamoDB → S3 Export → QuickSight → Dashboard
```

## Security Considerations

### IAM Roles and Policies
- **Lambda Execution Role**: Minimal permissions for DynamoDB, CloudWatch, Cost Explorer
- **QuickSight Role**: Read-only access to data sources
- **SNS Publishing Role**: Publish permissions to notification topics

### Data Encryption
- **DynamoDB**: Encryption at rest enabled
- **S3**: Server-side encryption for QuickSight data
- **SNS**: Message encryption in transit

### Access Control
- **API Gateway**: Optional for external integrations
- **VPC**: Lambda functions in private subnets (if required)
- **Resource-based Policies**: Restrict access to specific resources

## Scalability and Performance

### Auto Scaling
- **DynamoDB**: On-demand billing mode for automatic scaling
- **Lambda**: Concurrent execution limits configured
- **QuickSight**: SPICE capacity management

### Performance Optimization
- **DynamoDB**: Efficient partition key design
- **Lambda**: Connection pooling and caching
- **QuickSight**: Incremental data refresh

### Cost Optimization
- **Lambda**: Right-sized memory allocation
- **DynamoDB**: TTL for historical data cleanup
- **S3**: Lifecycle policies for data archival

## Monitoring and Observability

### CloudWatch Metrics
- Lambda function performance
- DynamoDB read/write capacity
- Error rates and latencies

### CloudWatch Logs
- Structured logging for all Lambda functions
- Error tracking and debugging
- Performance monitoring

### X-Ray Tracing
- End-to-end request tracing
- Performance bottleneck identification
- Service map visualization

## Disaster Recovery

### Backup Strategy
- **DynamoDB**: Point-in-time recovery enabled
- **Configuration**: Version-controlled infrastructure
- **Data Export**: Regular S3 backups

### Multi-Region Considerations
- **Primary Region**: us-east-1 (for Cost Explorer API)
- **Backup Region**: Configurable for disaster recovery
- **Data Replication**: Cross-region DynamoDB replication (optional)

## Deployment Architecture

### Infrastructure as Code
- **AWS CDK**: TypeScript/Python for infrastructure
- **CloudFormation**: Generated templates
- **CI/CD**: Automated deployment pipeline

### Environment Management
- **Development**: Isolated stack for testing
- **Staging**: Pre-production validation
- **Production**: Live cost monitoring system

This architecture provides a robust, scalable, and cost-effective solution for AWS cost monitoring and optimization.
