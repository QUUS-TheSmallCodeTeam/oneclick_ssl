"""
Configuration constants and settings for SecureCheck Pro
"""

from typing import Dict, Any

# SSL Grade Scoring
SSL_GRADE_SCORES: Dict[str, int] = {
    'A+': 95,
    'A': 90,
    'A-': 85,
    'B': 75,
    'C': 60,
    'D': 40,
    'F': 15
}

# Business Impact Constants
BUSINESS_IMPACT_CONFIG = {
    'base_revenue': 1_000_000_000,  # Base revenue for calculations
    'monthly_visitors': 10000,
    'conversion_rate': 0.02,
    'order_conversion': 0.1,
    'avg_order_value': 50000000,
    
    # SSL Status Impact Multipliers
    'ssl_impact': {
        'no_ssl': {
            'revenue_loss': 1_008_000_000,
            'seo_impact': 35,
            'trust_impact': 80
        },
        'expired': {
            'revenue_loss': 600_000_000,
            'seo_impact': 25,
            'trust_impact': 70
        },
        'self_signed': {
            'revenue_loss': 400_000_000,
            'seo_impact': 20,
            'trust_impact': 60
        },
        'connection_error': {
            'revenue_loss': 800_000_000,
            'seo_impact': 30,
            'trust_impact': 75
        }
    }
}

# Security Scoring
SECURITY_SCORING = {
    'ssl_status_scores': {
        'no_ssl': 0,
        'expired': 10,
        'self_signed': 25,
        'verify_failed': 30,
        'connection_error': 0
    },
    'header_penalty': 3,  # Points deducted per missing header
    'expiry_penalty': 10,  # Points deducted when cert expires in < 30 days
    'max_loss_rate': 0.15  # Maximum 15% revenue loss
}

# Critical Security Headers
CRITICAL_SECURITY_HEADERS = [
    'Strict-Transport-Security',
    'Content-Security-Policy',
    'X-Frame-Options'
]

# SSL Certificate Thresholds
CERTIFICATE_THRESHOLDS = {
    'critical_expiry_days': 7,
    'warning_expiry_days': 30,
    'renewal_recommendation_days': 60
}

# Severity Mappings
SEVERITY_LEVELS = {
    'critical': {
        'priority': 1,
        'color': '#c0392b',
        'emoji': '🔴'
    },
    'high': {
        'priority': 2,
        'color': '#e74c3c',
        'emoji': '🟠'
    },
    'medium': {
        'priority': 3,
        'color': '#f39c12',
        'emoji': '🟡'
    },
    'low': {
        'priority': 4,
        'color': '#27ae60',
        'emoji': '🟢'
    }
}

# PDF Generation
PDF_CONFIG = {
    'fonts': {
        'korean': '/fonts/NotoSansKR-Regular.ttf',
        'korean_bold': '/fonts/NotoSansKR-Bold.ttf'
    },
    'styles': {
        'title_size': 18,
        'heading_size': 14,
        'body_size': 11,
        'code_size': 9
    },
    'margins': {
        'top': 50,
        'bottom': 50,
        'left': 50,
        'right': 50
    }
}

# API Configuration
API_CONFIG = {
    'cors_origins': ["*"],  # In production, restrict this
    'timeout': 30,
    'max_retries': 3
}