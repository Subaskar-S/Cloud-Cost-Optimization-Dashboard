# AWS Cloud Cost Optimization Dashboard

A fully serverless AWS cost monitoring and optimization platform that helps teams track cloud expenses, visualize trends, and take action to reduce unnecessary spend.

## 🏗️ Architecture Overview

This platform uses a serverless, event-driven architecture:

```
CloudWatch Events (Cron) → Lambda Functions → DynamoDB → QuickSight Dashboard
                                    ↓
                              SNS Alerts ← Cost Analysis
```

## 🧰 Tech Stack

- **AWS CloudWatch**: Usage and billing metrics collection
- **AWS Lambda**: Data collection, processing, and analysis
- **AWS DynamoDB**: Cost data storage with optimized queries
- **Amazon QuickSight**: Interactive dashboard visualization
- **AWS Cost Explorer API**: Detailed cost and usage data
- **Amazon SNS**: Alerting and notifications
- **Python 3.9+**: Lambda runtime and scripting
- **AWS CDK/CloudFormation**: Infrastructure as Code

## 📂 Project Structure

```
├── lambda/                     # Lambda function code
│   ├── data_collection/       # Cost data collection functions
│   ├── data_processing/       # Analysis and optimization logic
│   └── alerting/             # Notification and alert functions
├── infrastructure/            # AWS CDK/CloudFormation templates
│   ├── dynamodb/             # DynamoDB table definitions
│   ├── lambda/               # Lambda function configurations
│   └── iam/                  # IAM roles and policies
├── config/                   # Configuration files
│   ├── thresholds.json       # Cost alert thresholds
│   └── budgets.json          # Budget targets by service
├── visualization/            # QuickSight configurations
│   ├── datasets/             # Dataset definitions
│   └── dashboards/           # Dashboard templates
├── docs/                     # Documentation
│   ├── architecture.md       # System architecture details
│   ├── deployment.md         # Deployment instructions
│   └── user_guide.md         # User manual
└── tests/                    # Test scenarios and validation
    ├── unit/                 # Unit tests
    └── integration/          # Integration tests
```

## 🚀 Quick Start

1. **Prerequisites**
   - AWS CLI configured with appropriate permissions
   - Python 3.9+ installed
   - AWS CDK installed (`npm install -g aws-cdk`)

2. **Deploy Infrastructure**
   ```bash
   cd infrastructure
   cdk deploy
   ```

3. **Configure QuickSight**
   - Follow the setup guide in `docs/deployment.md`

4. **Set Up Alerts**
   - Configure thresholds in `config/thresholds.json`
   - Deploy alerting functions

## 📊 Features

### Data Collection
- Automated hourly/daily cost data collection
- Multi-region and multi-service monitoring
- Tag-based cost attribution
- Historical data retention

### Cost Analysis
- Daily/weekly/monthly usage summaries
- High-cost service identification
- Usage spike detection
- Over-provisioned resource reports
- Idle resource identification

### Visualization
- Real-time cost dashboards
- Service-wise trend analysis
- Regional cost breakdown
- Budget vs actual spending
- Forecasting and projections

### Alerting
- Configurable cost thresholds
- Anomaly detection
- Email and Slack notifications
- Weekly summary reports

## 🔧 Configuration

### Cost Thresholds
Edit `config/thresholds.json` to set alert thresholds:

```json
{
  "daily_threshold": 100,
  "weekly_threshold": 500,
  "monthly_threshold": 2000,
  "service_thresholds": {
    "EC2": 50,
    "S3": 20,
    "Lambda": 10
  }
}
```

### Budget Targets
Configure budget targets in `config/budgets.json`:

```json
{
  "monthly_budget": 2500,
  "service_budgets": {
    "EC2": 1000,
    "S3": 300,
    "Lambda": 200,
    "RDS": 500
  }
}
```

## 📈 Dashboard Features

- **Cost Overview**: Total spend, trends, and forecasts
- **Service Breakdown**: Cost by AWS service with drill-down
- **Regional Analysis**: Spending by AWS region
- **Tag-based Views**: Cost attribution by project/team/environment
- **Optimization Recommendations**: Actionable insights for cost reduction

## 🔔 Alerting System

- **Threshold Alerts**: Notifications when costs exceed predefined limits
- **Anomaly Detection**: ML-based detection of unusual spending patterns
- **Budget Tracking**: Alerts when approaching budget limits
- **Weekly Reports**: Automated summary emails with key insights

## 🧪 Testing

Run the test suite to validate functionality:

```bash
# Unit tests
python -m pytest tests/unit/

# Integration tests
python -m pytest tests/integration/
```

## 📚 Documentation

- [Architecture Details](docs/architecture.md)
- [Deployment Guide](docs/deployment.md)
- [User Guide](docs/user_guide.md)
- [API Reference](docs/api_reference.md)

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

We welcome contributions to improve the AWS Cost Optimization Dashboard! Here's how to get started:

### 🔄 Development Workflow

1. **Fork the Repository**
   ```bash
   # Click the "Fork" button on GitHub or use GitHub CLI
   gh repo fork Subaskar-S/aws-cost-optimization-dashboard
   ```

2. **Clone Your Fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/aws-cost-optimization-dashboard.git
   cd aws-cost-optimization-dashboard
   ```

3. **Create a Feature Branch**
   ```bash
   # Use descriptive branch names
   git checkout -b feature/add-azure-cost-support
   git checkout -b fix/lambda-timeout-issue
   git checkout -b docs/update-deployment-guide
   ```

4. **Make Your Changes**
   - Follow the existing code style and patterns
   - Add tests for new functionality
   - Update documentation as needed
   - Test your changes locally

5. **Commit Your Changes**
   ```bash
   # Use clear, descriptive commit messages
   git add .
   git commit -m "Add Azure cost collection support with error handling"
   git commit -m "Fix Lambda timeout in data processing for large datasets"
   git commit -m "Update deployment guide with new IAM permissions"
   ```

6. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-branch-name
   # Then create a PR through GitHub UI
   ```

### 📋 Contribution Guidelines

- **Code Quality**: Follow Python PEP 8 standards and existing patterns
- **Testing**: Add unit tests for new features (`tests/unit/`)
- **Documentation**: Update relevant docs in the `docs/` folder
- **Security**: Never commit secrets or credentials
- **Performance**: Consider impact on Lambda execution time and DynamoDB costs

### 🐛 Bug Reports

When reporting bugs, please include:
- Steps to reproduce the issue
- Expected vs actual behavior
- AWS region and service versions
- Relevant log snippets (sanitized)

### 💡 Feature Requests

For new features, please:
- Check existing issues first
- Describe the use case and business value
- Consider implementation complexity
- Discuss breaking changes

## 👨‍💻 Made by

**Subaskar_S**

[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Subaskar-S)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/subaskar97)

---

### 🌟 If this project helped you save money on AWS costs, please give it a star!

**Built with ❤️ for cloud cost optimization**
