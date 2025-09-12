"""
SSL Analysis Service - Consolidated SSL analysis logic
"""

from typing import Dict, Any, List
from config import (
    SSL_GRADE_SCORES, BUSINESS_IMPACT_CONFIG, SECURITY_SCORING,
    CRITICAL_SECURITY_HEADERS, CERTIFICATE_THRESHOLDS
)


class SSLAnalysisService:
    """Service class for SSL analysis operations"""
    
    @staticmethod
    def generate_issues_from_ssl_result(ssl_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate issues list from SSL analysis result"""
        issues = []
        
        # Certificate expiry check
        days_until_expiry = ssl_result.get("days_until_expiry", 0)
        if days_until_expiry < CERTIFICATE_THRESHOLDS['warning_expiry_days']:
            severity = "high" if days_until_expiry < CERTIFICATE_THRESHOLDS['critical_expiry_days'] else "medium"
            issues.append({
                "title": "SSL 인증서 만료 임박",
                "description": f"인증서가 {days_until_expiry}일 후 만료됩니다. 갱신이 필요합니다.",
                "severity": severity
            })
        
        # Certificate validity
        if not ssl_result.get("certificate_valid", True):
            issues.append({
                "title": "유효하지 않은 SSL 인증서",
                "description": "SSL 인증서가 유효하지 않습니다. 인증서를 확인하고 교체하세요.",
                "severity": "critical"
            })
        
        # Self-signed certificate
        if ssl_result.get("is_self_signed", False):
            issues.append({
                "title": "자체 서명 인증서 사용",
                "description": "자체 서명된 인증서를 사용하고 있습니다. 신뢰할 수 있는 CA에서 발급받은 인증서로 교체하세요.",
                "severity": "high"
            })
        
        # Missing security headers
        missing_headers = ssl_result.get("missing_security_headers", [])
        if missing_headers:
            critical_missing = [h for h in missing_headers if h in CRITICAL_SECURITY_HEADERS]
            
            if critical_missing:
                issues.append({
                    "title": "중요 보안 헤더 누락",
                    "description": f"다음 중요 보안 헤더가 누락되었습니다: {', '.join(critical_missing)}",
                    "severity": "high"
                })
            
            other_missing = [h for h in missing_headers if h not in CRITICAL_SECURITY_HEADERS]
            if other_missing:
                issues.append({
                    "title": "보안 헤더 누락",
                    "description": f"다음 보안 헤더가 누락되었습니다: {', '.join(other_missing)}",
                    "severity": "medium"
                })
        
        # HSTS disabled
        if not ssl_result.get("hsts_enabled", False):
            issues.append({
                "title": "HSTS (HTTP Strict Transport Security) 비활성화",
                "description": "HSTS 헤더가 설정되지 않아 중간자 공격에 취약할 수 있습니다.",
                "severity": "medium"
            })
        
        return issues
    
    @staticmethod
    def generate_recommendations_from_ssl_result(ssl_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations from SSL analysis result"""
        recommendations = []
        
        # SSL grade-based recommendations
        ssl_grade = ssl_result.get("ssl_grade", "F")
        if ssl_grade in ["F", "D", "C"]:
            recommendations.extend([
                "SSL 구성을 전면적으로 검토하고 최신 보안 프로토콜을 적용하세요.",
                "약한 암호화 스위트를 비활성화하고 강력한 암호화를 사용하세요."
            ])
        elif ssl_grade == "B":
            recommendations.append("SSL 구성을 개선하여 A 등급을 목표로 하세요.")
        
        # Security header recommendations
        missing_headers = ssl_result.get("missing_security_headers", [])
        header_recommendations = {
            "Strict-Transport-Security": "HSTS (HTTP Strict Transport Security) 헤더를 설정하여 HTTPS 연결을 강제하세요.",
            "Content-Security-Policy": "CSP (Content Security Policy) 헤더를 설정하여 XSS 공격을 방지하세요.",
            "X-Frame-Options": "X-Frame-Options 헤더를 설정하여 클릭재킹 공격을 방지하세요."
        }
        
        for header in missing_headers:
            if header in header_recommendations:
                recommendations.append(header_recommendations[header])
        
        # Certificate expiry recommendations
        days_until_expiry = ssl_result.get("days_until_expiry", 0)
        if days_until_expiry < CERTIFICATE_THRESHOLDS['renewal_recommendation_days']:
            recommendations.append("SSL 인증서 자동 갱신 시스템을 구축하여 만료를 방지하세요.")
        
        # Default recommendations
        if not recommendations:
            recommendations.extend([
                "정기적인 보안 점검을 통해 보안 상태를 유지하세요.",
                "보안 헤더 및 SSL 구성을 주기적으로 모니터링하세요."
            ])
        
        return recommendations
    
    @staticmethod
    def calculate_security_score(ssl_result: Dict[str, Any]) -> int:
        """Calculate security score based on SSL analysis results"""
        ssl_status = ssl_result.get('ssl_status', 'connection_error')
        
        # Base score from SSL status
        if ssl_status in SECURITY_SCORING['ssl_status_scores']:
            score = SECURITY_SCORING['ssl_status_scores'][ssl_status]
        elif ssl_status == 'valid':
            # Valid SSL - calculate based on grade
            ssl_grade = ssl_result.get("ssl_grade", "B")
            score = SSL_GRADE_SCORES.get(ssl_grade, 40)
            
            # Apply penalties
            missing_headers = ssl_result.get("missing_security_headers", [])
            score -= len(missing_headers) * SECURITY_SCORING['header_penalty']
            
            # Certificate expiry penalty
            days_until_expiry = ssl_result.get('days_until_expiry', 0)
            if days_until_expiry < CERTIFICATE_THRESHOLDS['warning_expiry_days']:
                score -= SECURITY_SCORING['expiry_penalty']
        else:
            score = 0
        
        return max(0, score)
    
    @staticmethod
    def extract_security_issues(ssl_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract security issues from SSL analysis result"""
        issues = []
        ssl_status = ssl_result.get('ssl_status', 'connection_error')
        
        # SSL service issues
        if ssl_status == 'no_ssl' or not ssl_result.get('port_443_open', False):
            issues.extend([
                {
                    "type": "ssl_service",
                    "severity": "critical",
                    "title": "HTTPS 서비스 완전 부재",
                    "description": "443 포트가 닫혀있어 HTTPS 서비스가 전혀 제공되지 않습니다."
                },
                {
                    "type": "data_encryption",
                    "severity": "critical",
                    "title": "모든 데이터 평문 전송",
                    "description": "암호화 없이 모든 데이터가 평문으로 전송되어 도청 위험에 노출됩니다."
                },
                {
                    "type": "browser_warning",
                    "severity": "high",
                    "title": "브라우저 보안 경고",
                    "description": "모든 브라우저에서 '안전하지 않음' 경고 메시지가 표시됩니다."
                }
            ])
        
        # Certificate issues
        certificate_issues = {
            'expired': {
                "type": "certificate",
                "severity": "critical",
                "title": "SSL 인증서 만료",
                "description": "SSL 인증서가 만료되어 브라우저에서 보안 경고를 표시합니다."
            },
            'self_signed': {
                "type": "certificate",
                "severity": "high",
                "title": "자체 서명 인증서",
                "description": "신뢰할 수 있는 인증기관에서 발급하지 않은 인증서로, 브라우저에서 경고를 표시합니다."
            },
            'verify_failed': {
                "type": "certificate",
                "severity": "critical",
                "title": "SSL 인증서 검증 실패",
                "description": "브라우저에서 SSL 인증서를 신뢰할 수 없습니다. 인증 기관이 유효하지 않거나 체인이 불완전합니다."
            }
        }
        
        if ssl_status in certificate_issues:
            issues.append(certificate_issues[ssl_status])
        
        # Security header issues
        missing_headers = ssl_result.get("missing_security_headers", [])
        for header in missing_headers:
            issues.append({
                "type": "security_header",
                "severity": "medium",
                "title": f"{header} 헤더 누락",
                "description": f"{header} 보안 헤더가 설정되지 않았습니다."
            })
        
        # Certificate expiry warning
        if ssl_status == 'valid':
            days_until_expiry = ssl_result.get('days_until_expiry', 0)
            if 0 < days_until_expiry < CERTIFICATE_THRESHOLDS['warning_expiry_days']:
                issues.append({
                    "type": "certificate",
                    "severity": "medium",
                    "title": "SSL 인증서 만료 임박",
                    "description": f"SSL 인증서가 {days_until_expiry}일 후에 만료됩니다."
                })
        
        return issues