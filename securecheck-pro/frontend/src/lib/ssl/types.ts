// SSL 분석 결과 타입 정의
export interface SSLAnalysisResult {
  domain: string;
  port: number;
  analyzed_at: string;
  url_scheme: string;
  port_443_open: boolean;
  ssl_grade: 'A+' | 'A' | 'B' | 'C' | 'D' | 'F';
  certificate_valid: boolean;
  ssl_status: 'valid' | 'expired' | 'self_signed' | 'verify_failed' | 'no_ssl' | 'connection_error';
  analysis_result: string;
  days_until_expiry?: number;
  is_self_signed?: boolean;
  certificate_issuer?: string;
  certificate_subject?: string;
  certificate_start_date?: string;
  certificate_end_date?: string;
  missing_security_headers: string[];
  hsts_enabled: boolean;
  security_headers: Record<string, string>;
}

export interface SecurityIssue {
  type: 'ssl_service' | 'certificate' | 'security_header' | 'data_encryption' | 'browser_warning';
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
}

export interface BusinessImpact {
  revenue_loss_annual?: number;
  seo_impact?: number;
  user_trust_impact?: number;
}

export interface SecurityConfig {
  SSL_GRADE_SCORES: Record<string, number>;
  BUSINESS_IMPACT_CONFIG: {
    revenue_loss_per_grade: Record<string, number>;
    seo_impact_per_grade: Record<string, number>;
    user_trust_impact_per_grade: Record<string, number>;
  };
  SECURITY_SCORING: {
    ssl_status_scores: Record<string, number>;
    header_penalty: number;
    expiry_penalty: number;
  };
  CRITICAL_SECURITY_HEADERS: string[];
  CERTIFICATE_THRESHOLDS: {
    warning_expiry_days: number;
    critical_expiry_days: number;
    renewal_recommendation_days: number;
  };
}