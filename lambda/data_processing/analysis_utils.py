"""
Utility functions for cost data analysis and processing
"""

import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import mean, median, stdev
import math
import logging

logger = logging.getLogger(__name__)


def calculate_cost_efficiency_score(cost_data, usage_data=None):
    """
    Calculate a cost efficiency score based on cost trends and usage patterns
    """
    if not cost_data:
        return 0
    
    # Group by service and calculate efficiency metrics
    service_metrics = {}
    
    for record in cost_data:
        service = record.get('service_name', 'Unknown')
        cost = float(record.get('cost_amount', 0))
        usage = float(record.get('usage_quantity', 0))
        
        if service not in service_metrics:
            service_metrics[service] = {
                'costs': [],
                'usage': [],
                'cost_per_unit': []
            }
        
        service_metrics[service]['costs'].append(cost)
        service_metrics[service]['usage'].append(usage)
        
        if usage > 0:
            service_metrics[service]['cost_per_unit'].append(cost / usage)
    
    # Calculate efficiency score (0-100)
    total_score = 0
    service_count = 0
    
    for service, metrics in service_metrics.items():
        if len(metrics['costs']) < 2:
            continue
            
        # Cost stability (lower variance is better)
        cost_variance = stdev(metrics['costs']) / mean(metrics['costs']) if mean(metrics['costs']) > 0 else 1
        stability_score = max(0, 100 - (cost_variance * 100))
        
        # Usage efficiency (consistent usage patterns)
        if metrics['usage'] and len(metrics['usage']) > 1:
            usage_variance = stdev(metrics['usage']) / mean(metrics['usage']) if mean(metrics['usage']) > 0 else 1
            usage_score = max(0, 100 - (usage_variance * 50))
        else:
            usage_score = 50
        
        # Cost per unit efficiency
        if metrics['cost_per_unit'] and len(metrics['cost_per_unit']) > 1:
            cpu_variance = stdev(metrics['cost_per_unit']) / mean(metrics['cost_per_unit']) if mean(metrics['cost_per_unit']) > 0 else 1
            cpu_score = max(0, 100 - (cpu_variance * 75))
        else:
            cpu_score = 50
        
        service_score = (stability_score * 0.4 + usage_score * 0.3 + cpu_score * 0.3)
        total_score += service_score
        service_count += 1
    
    return round(total_score / service_count if service_count > 0 else 0, 1)


def detect_cost_anomalies(cost_data, sensitivity='medium'):
    """
    Detect cost anomalies using statistical methods
    """
    anomalies = []
    
    # Group by service and date
    service_daily_costs = {}
    
    for record in cost_data:
        service = record.get('service_name', 'Unknown')
        date = record['timestamp'][:10]
        cost = float(record.get('cost_amount', 0))
        
        if service not in service_daily_costs:
            service_daily_costs[service] = {}
        
        if date not in service_daily_costs[service]:
            service_daily_costs[service][date] = 0
        
        service_daily_costs[service][date] += cost
    
    # Set sensitivity thresholds
    sensitivity_thresholds = {
        'low': 3.0,
        'medium': 2.5,
        'high': 2.0
    }
    threshold = sensitivity_thresholds.get(sensitivity, 2.5)
    
    # Detect anomalies for each service
    for service, daily_costs in service_daily_costs.items():
        costs = list(daily_costs.values())
        
        if len(costs) < 7:  # Need at least a week of data
            continue
        
        # Calculate rolling statistics
        cost_mean = mean(costs)
        cost_std = stdev(costs) if len(costs) > 1 else 0
        
        # Find anomalies
        for date, cost in daily_costs.items():
            if cost_std > 0:
                z_score = abs(cost - cost_mean) / cost_std
                
                if z_score > threshold:
                    anomaly = {
                        'service': service,
                        'date': date,
                        'cost': Decimal(str(round(cost, 2))),
                        'expected_cost': Decimal(str(round(cost_mean, 2))),
                        'deviation': Decimal(str(round(z_score, 2))),
                        'severity': 'high' if z_score > 3 else 'medium' if z_score > 2 else 'low',
                        'type': 'spike' if cost > cost_mean else 'drop'
                    }
                    anomalies.append(anomaly)
    
    return sorted(anomalies, key=lambda x: x['deviation'], reverse=True)


def calculate_forecast(cost_data, forecast_days=30):
    """
    Calculate cost forecast using simple linear regression
    """
    # Group by date
    daily_costs = {}
    for record in cost_data:
        date = record['timestamp'][:10]
        cost = float(record.get('cost_amount', 0))
        
        if date not in daily_costs:
            daily_costs[date] = 0
        daily_costs[date] += cost
    
    # Sort by date
    sorted_dates = sorted(daily_costs.keys())
    if len(sorted_dates) < 7:
        return None
    
    costs = [daily_costs[date] for date in sorted_dates]
    
    # Simple linear regression
    n = len(costs)
    x_values = list(range(n))
    
    x_mean = mean(x_values)
    y_mean = mean(costs)
    
    numerator = sum((x_values[i] - x_mean) * (costs[i] - y_mean) for i in range(n))
    denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
    
    if denominator == 0:
        return None
    
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    
    # Generate forecast
    forecast = []
    last_date = datetime.strptime(sorted_dates[-1], '%Y-%m-%d').date()
    
    for i in range(1, forecast_days + 1):
        forecast_date = last_date + timedelta(days=i)
        forecast_cost = slope * (n + i - 1) + intercept
        
        forecast.append({
            'date': forecast_date.strftime('%Y-%m-%d'),
            'forecasted_cost': max(0, round(forecast_cost, 2))  # Ensure non-negative
        })
    
    return {
        'forecast': forecast,
        'trend': 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable',
        'daily_change': round(slope, 2),
        'confidence': min(100, max(0, 100 - abs(slope) * 10))  # Simple confidence metric
    }


def identify_cost_drivers(cost_data, top_n=10):
    """
    Identify the top cost drivers by service, region, and resource
    """
    drivers = {
        'services': {},
        'regions': {},
        'resources': {}
    }
    
    total_cost = 0
    
    for record in cost_data:
        cost = float(record.get('cost_amount', 0))
        total_cost += cost
        
        # Service drivers
        service = record.get('service_name', 'Unknown')
        drivers['services'][service] = drivers['services'].get(service, 0) + cost
        
        # Regional drivers
        region = record.get('region', 'unknown')
        drivers['regions'][region] = drivers['regions'].get(region, 0) + cost
        
        # Resource drivers
        resource = record.get('resource_id')
        if resource:
            drivers['resources'][resource] = drivers['resources'].get(resource, 0) + cost
    
    # Sort and format results
    result = {}
    
    for category, data in drivers.items():
        sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        result[category] = [
            {
                'name': item[0],
                'cost': Decimal(str(round(item[1], 2))),
                'percentage': Decimal(str(round((item[1] / total_cost * 100) if total_cost > 0 else 0, 2)))
            }
            for item in sorted_items
        ]
    
    return result


def calculate_savings_opportunities(cost_data, recommendations_data=None):
    """
    Calculate potential savings opportunities
    """
    opportunities = {
        'rightsizing': 0,
        'reserved_instances': 0,
        'idle_resources': 0,
        'storage_optimization': 0,
        'total_potential': 0
    }
    
    # Analyze EC2 costs for rightsizing opportunities
    ec2_costs = [
        float(record.get('cost_amount', 0))
        for record in cost_data
        if 'Compute' in record.get('service_name', '')
    ]
    
    if ec2_costs:
        # Assume 15-30% savings potential from rightsizing
        ec2_total = sum(ec2_costs)
        opportunities['rightsizing'] = ec2_total * 0.2
    
    # Analyze for reserved instance opportunities
    # Look for consistent usage patterns
    service_usage = {}
    for record in cost_data:
        service = record.get('service_name', '')
        if 'Compute' in service or 'Database' in service:
            date = record['timestamp'][:10]
            cost = float(record.get('cost_amount', 0))
            
            if service not in service_usage:
                service_usage[service] = {}
            service_usage[service][date] = service_usage[service].get(date, 0) + cost
    
    for service, daily_costs in service_usage.items():
        if len(daily_costs) >= 30:  # At least a month of data
            costs = list(daily_costs.values())
            if min(costs) > 0:  # Consistent usage
                avg_cost = mean(costs)
                # Assume 20-40% savings with reserved instances
                opportunities['reserved_instances'] += avg_cost * 30 * 0.3
    
    # Estimate idle resource savings (10% of total cost)
    total_cost = sum(float(record.get('cost_amount', 0)) for record in cost_data)
    opportunities['idle_resources'] = total_cost * 0.1
    
    # Storage optimization (5% of storage costs)
    storage_costs = [
        float(record.get('cost_amount', 0))
        for record in cost_data
        if 'Storage' in record.get('service_name', '') or 'S3' in record.get('service_name', '')
    ]
    
    if storage_costs:
        opportunities['storage_optimization'] = sum(storage_costs) * 0.05
    
    # Calculate total potential
    opportunities['total_potential'] = sum(
        opportunities[key] for key in opportunities if key != 'total_potential'
    )
    
    # Convert to Decimal for JSON serialization
    return {
        key: Decimal(str(round(value, 2)))
        for key, value in opportunities.items()
    }


def generate_cost_insights(cost_data):
    """
    Generate actionable cost insights
    """
    insights = []
    
    # Analyze cost trends
    daily_costs = {}
    for record in cost_data:
        date = record['timestamp'][:10]
        cost = float(record.get('cost_amount', 0))
        daily_costs[date] = daily_costs.get(date, 0) + cost
    
    if len(daily_costs) >= 7:
        costs = list(daily_costs.values())
        recent_avg = mean(costs[-7:])
        
        if len(costs) >= 14:
            previous_avg = mean(costs[-14:-7])
            change = (recent_avg - previous_avg) / previous_avg * 100
            
            if change > 20:
                insights.append({
                    'type': 'cost_increase',
                    'severity': 'high',
                    'message': f'Costs increased by {change:.1f}% in the last week',
                    'recommendation': 'Review recent resource changes and usage patterns'
                })
            elif change > 10:
                insights.append({
                    'type': 'cost_increase',
                    'severity': 'medium',
                    'message': f'Costs increased by {change:.1f}% in the last week',
                    'recommendation': 'Monitor cost trends and investigate drivers'
                })
    
    # Analyze service distribution
    service_costs = {}
    total_cost = 0
    
    for record in cost_data:
        service = record.get('service_name', 'Unknown')
        cost = float(record.get('cost_amount', 0))
        service_costs[service] = service_costs.get(service, 0) + cost
        total_cost += cost
    
    # Check for cost concentration
    if service_costs:
        top_service_cost = max(service_costs.values())
        if top_service_cost / total_cost > 0.7:
            top_service = max(service_costs.items(), key=lambda x: x[1])[0]
            insights.append({
                'type': 'cost_concentration',
                'severity': 'medium',
                'message': f'{top_service} accounts for {top_service_cost/total_cost*100:.1f}% of total costs',
                'recommendation': 'Consider optimization opportunities for this service'
            })
    
    return insights
