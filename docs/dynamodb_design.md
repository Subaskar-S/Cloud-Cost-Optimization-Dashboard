# DynamoDB Table Design for Cost Optimization Dashboard

## Overview

The Cost Optimization Dashboard uses five main DynamoDB tables to store cost data, analysis results, configuration, alerts, and optimization recommendations. Each table is designed for optimal performance and cost-effectiveness using DynamoDB best practices.

## Table Schemas

### 1. Cost Data Table (`cost-data`)

**Purpose**: Store raw cost and usage data from AWS Cost Explorer and CloudWatch metrics.

**Schema**:
- **Partition Key**: `service_id` (String) - Format: `{service_name}#{region}`
- **Sort Key**: `timestamp` (String) - ISO 8601 format
- **TTL**: `ttl` (Number) - Unix timestamp for automatic data expiration (90 days)

**Attributes**:
```json
{
  "service_id": "Amazon Elastic Compute Cloud - Compute#us-east-1",
  "timestamp": "2024-01-15T00:00:00Z",
  "service_name": "Amazon Elastic Compute Cloud - Compute",
  "region": "us-east-1",
  "cost_amount": 125.50,
  "usage_quantity": 744.0,
  "usage_unit": "Hrs",
  "currency": "USD",
  "tags": {
    "Environment": "production",
    "Team": "backend",
    "Project": "web-app"
  },
  "resource_id": "i-1234567890abcdef0",
  "collection_timestamp": "2024-01-15T01:00:00Z",
  "ttl": 1715731200
}
```

**Global Secondary Indexes**:

1. **Region-Timestamp Index** (`region-timestamp-index`)
   - Partition Key: `region`
   - Sort Key: `timestamp`
   - Use Case: Query costs by region over time

2. **Tag-Timestamp Index** (`tag-timestamp-index`)
   - Partition Key: `tag_key` (derived attribute)
   - Sort Key: `timestamp`
   - Use Case: Query costs by tag values over time

**Access Patterns**:
- Get cost data for a specific service in a region over time
- Get all costs for a region within a date range
- Get costs by tag values (Environment, Team, Project)
- Get recent cost data for alerting

### 2. Cost Analysis Table (`cost-analysis`)

**Purpose**: Store processed analysis results, trends, and aggregated data.

**Schema**:
- **Partition Key**: `analysis_type` (String) - Type of analysis (daily, weekly, monthly, trend)
- **Sort Key**: `period` (String) - Time period (YYYY-MM-DD, YYYY-WW, YYYY-MM)
- **TTL**: `ttl` (Number) - Unix timestamp for automatic data expiration (1 year)

**Attributes**:
```json
{
  "analysis_type": "daily_summary",
  "period": "2024-01-15",
  "total_cost": 1250.75,
  "service_breakdown": {
    "EC2": 500.25,
    "S3": 150.30,
    "Lambda": 75.20,
    "RDS": 300.00,
    "Other": 225.00
  },
  "regional_breakdown": {
    "us-east-1": 750.45,
    "us-west-2": 300.15,
    "eu-west-1": 200.15
  },
  "trends": {
    "cost_change_percent": 5.2,
    "usage_change_percent": 3.1,
    "top_growing_service": "Lambda",
    "cost_efficiency_score": 85.5
  },
  "recommendations": [
    {
      "type": "rightsizing",
      "resource_id": "i-1234567890abcdef0",
      "potential_savings": 50.00,
      "confidence": "high"
    }
  ],
  "created_at": "2024-01-15T02:00:00Z",
  "ttl": 1747651200
}
```

**Global Secondary Indexes**:

1. **Created-At Index** (`created-at-index`)
   - Partition Key: `created_at` (date part)
   - Use Case: Query recent analysis results

**Access Patterns**:
- Get daily/weekly/monthly cost summaries
- Get trend analysis for specific periods
- Get latest analysis results for dashboard
- Get historical analysis for comparison

### 3. Configuration Table (`cost-config`)

**Purpose**: Store system configuration, thresholds, budgets, and settings.

**Schema**:
- **Partition Key**: `config_type` (String) - Type of configuration
- **No Sort Key** - Single item per configuration type

**Attributes**:
```json
{
  "config_type": "thresholds",
  "cost_thresholds": {
    "daily": {"warning": 100, "critical": 200},
    "weekly": {"warning": 500, "critical": 1000},
    "monthly": {"warning": 2000, "critical": 4000}
  },
  "service_thresholds": {
    "EC2": {"daily": 50, "monthly": 1200},
    "S3": {"daily": 20, "monthly": 400}
  },
  "notification_settings": {
    "email": {
      "enabled": true,
      "recipients": ["devops@company.com"]
    },
    "slack": {
      "enabled": true,
      "webhook_url": "https://hooks.slack.com/..."
    }
  },
  "updated_at": "2024-01-15T00:00:00Z",
  "updated_by": "admin"
}
```

**Access Patterns**:
- Get threshold configurations for alerting
- Get budget settings for analysis
- Get notification preferences
- Update configuration settings

### 4. Alerts Table (`cost-alerts`)

**Purpose**: Store alert history, status, and tracking information.

**Schema**:
- **Partition Key**: `alert_id` (String) - Unique alert identifier
- **Sort Key**: `timestamp` (String) - When alert was triggered
- **TTL**: `ttl` (Number) - Unix timestamp for automatic cleanup (30 days)

**Attributes**:
```json
{
  "alert_id": "threshold_breach_ec2_us-east-1_20240115",
  "timestamp": "2024-01-15T10:30:00Z",
  "alert_type": "threshold_breach",
  "severity": "warning",
  "service": "EC2",
  "region": "us-east-1",
  "current_cost": 125.50,
  "threshold": 100.00,
  "message": "EC2 costs in us-east-1 exceeded warning threshold",
  "status": "active",
  "acknowledged": false,
  "acknowledged_by": null,
  "acknowledged_at": null,
  "resolved": false,
  "resolved_at": null,
  "notification_sent": true,
  "notification_channels": ["email", "slack"],
  "ttl": 1708099200
}
```

**Global Secondary Indexes**:

1. **Status-Timestamp Index** (`status-timestamp-index`)
   - Partition Key: `status`
   - Sort Key: `timestamp`
   - Use Case: Query active/resolved alerts

**Access Patterns**:
- Get active alerts for dashboard
- Get alert history for a service/region
- Get unacknowledged alerts
- Track alert resolution status

### 5. Recommendations Table (`cost-recommendations`)

**Purpose**: Store cost optimization recommendations and tracking.

**Schema**:
- **Partition Key**: `resource_id` (String) - AWS resource identifier
- **Sort Key**: `recommendation_type` (String) - Type of recommendation
- **TTL**: `ttl` (Number) - Unix timestamp for automatic cleanup (60 days)

**Attributes**:
```json
{
  "resource_id": "i-1234567890abcdef0",
  "recommendation_type": "rightsizing",
  "service": "EC2",
  "region": "us-east-1",
  "current_cost": 100.00,
  "estimated_savings": 30.00,
  "confidence": "high",
  "priority": "medium",
  "description": "Instance is over-provisioned based on CPU utilization",
  "recommended_action": "Downsize from m5.large to m5.medium",
  "implementation_effort": "low",
  "risk_level": "low",
  "created_at": "2024-01-15T00:00:00Z",
  "status": "open",
  "implemented": false,
  "implemented_at": null,
  "actual_savings": null,
  "tags": {
    "Environment": "production",
    "Team": "backend"
  },
  "ttl": 1710547200
}
```

**Global Secondary Indexes**:

1. **Priority-Savings Index** (`priority-savings-index`)
   - Partition Key: `priority`
   - Sort Key: `estimated_savings` (Number)
   - Use Case: Query recommendations by priority and potential savings

**Access Patterns**:
- Get recommendations for a specific resource
- Get high-priority recommendations
- Get recommendations with highest savings potential
- Track implementation status

## Query Patterns and Examples

### Common Query Patterns

1. **Get daily costs for a service**:
```python
response = table.query(
    KeyConditionExpression=Key('service_id').eq('EC2#us-east-1') & 
                          Key('timestamp').between('2024-01-01', '2024-01-31')
)
```

2. **Get costs by region**:
```python
response = table.query(
    IndexName='region-timestamp-index',
    KeyConditionExpression=Key('region').eq('us-east-1') & 
                          Key('timestamp').between('2024-01-01', '2024-01-31')
)
```

3. **Get active alerts**:
```python
response = alerts_table.query(
    IndexName='status-timestamp-index',
    KeyConditionExpression=Key('status').eq('active')
)
```

4. **Get high-priority recommendations**:
```python
response = recommendations_table.query(
    IndexName='priority-savings-index',
    KeyConditionExpression=Key('priority').eq('high'),
    ScanIndexForward=False  # Sort by savings descending
)
```

## Performance Considerations

### Partition Key Design
- Service-region combination provides good distribution
- Avoids hot partitions by spreading load across services and regions
- Time-based sort key enables efficient range queries

### Index Strategy
- GSIs support common query patterns without table scans
- Sparse indexes reduce storage costs
- Projection type ALL for flexibility vs. cost trade-off

### TTL Implementation
- Automatic data cleanup reduces storage costs
- Different retention periods based on data importance
- Raw data: 90 days, Analysis: 1 year, Alerts: 30 days

### Capacity Planning
- On-demand billing for variable workloads
- Monitor consumed capacity and adjust if needed
- Consider provisioned capacity for predictable workloads

## Cost Optimization

### Storage Optimization
- Use TTL for automatic data expiration
- Compress large attributes when possible
- Use sparse indexes to reduce index storage

### Query Optimization
- Use specific partition keys to avoid scans
- Limit result sets with pagination
- Use projection expressions to fetch only needed attributes

### Monitoring
- Set up CloudWatch alarms for throttling
- Monitor consumed vs. provisioned capacity
- Track storage utilization trends
