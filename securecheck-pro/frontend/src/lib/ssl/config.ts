// SSL 분석 설정값들
export const SSL_GRADE_SCORES = {
  'A+': 95,
  'A': 85,
  'B': 70,
  'C': 50,
  'D': 30,
  'F': 10
} as const;

export const BUSINESS_IMPACT_CONFIG = {
  revenue_loss_per_grade: {
    'F': 2000000,
    'D': 1500000,
    'C': 1000000,
    'B': 500000,
    'A': 200000,
    'A+': 100000
  },
  seo_impact_per_grade: {
    'F': 30,
    'D': 25,
    'C': 20,
    'B': 15,
    'A': 10,
    'A+': 5
  },
  user_trust_impact_per_grade: {
    'F': 50,
    'D': 40,
    'C': 30,
    'B': 20,
    'A': 10,
    'A+': 5
  }
} as const;

export const SECURITY_SCORING = {
  ssl_status_scores: {
    'no_ssl': 0,
    'connection_error': 0,
    'expired': 10,
    'self_signed': 20,
    'verify_failed': 15
  },
  header_penalty: 5,
  expiry_penalty: 10
} as const;

export const CRITICAL_SECURITY_HEADERS = [
  'Strict-Transport-Security',
  'Content-Security-Policy',
  'X-Frame-Options'
] as const;

export const CERTIFICATE_THRESHOLDS = {
  warning_expiry_days: 30,
  critical_expiry_days: 7,
  renewal_recommendation_days: 60
} as const;

export const SECURITY_HEADERS = [
  'Strict-Transport-Security',
  'Content-Security-Policy', 
  'X-Frame-Options',
  'X-Content-Type-Options',
  'X-XSS-Protection',
  'Referrer-Policy'
] as const;