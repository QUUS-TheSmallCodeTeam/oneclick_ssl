"""
Business Impact Service - Handles business impact calculations
"""

from typing import Dict, Any, List
from config import BUSINESS_IMPACT_CONFIG


class BusinessImpactService:
    """Service class for calculating business impact of security issues"""
    
    @staticmethod
    def calculate_business_impact(
        security_score: int, 
        ssl_result: Dict[str, Any], 
        issues: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Calculate business impact based on security analysis"""
        ssl_status = ssl_result.get('ssl_status', 'connection_error')
        
        # Check for specific SSL status impacts
        if ssl_status in BUSINESS_IMPACT_CONFIG['ssl_impact']:
            return BUSINESS_IMPACT_CONFIG['ssl_impact'][ssl_status]
        
        # Handle valid SSL with varying security scores
        if ssl_status == 'valid':
            return BusinessImpactService._calculate_valid_ssl_impact(security_score)
        
        # Default for unknown statuses
        return BUSINESS_IMPACT_CONFIG['ssl_impact']['connection_error']
    
    @staticmethod
    def _calculate_valid_ssl_impact(security_score: int) -> Dict[str, int]:
        """Calculate impact for valid SSL certificates based on security score"""
        base_config = BUSINESS_IMPACT_CONFIG
        base_revenue = base_config['base_revenue']
        max_loss_rate = 0.15  # Maximum 15% loss
        
        # Calculate loss rate based on security score
        loss_rate = max(0, (100 - security_score) / 100 * max_loss_rate)
        revenue_loss = int(base_revenue * loss_rate)
        
        # Calculate SEO and trust impact
        seo_impact = max(0, (100 - security_score) // 15)  # Max 6%
        trust_impact = max(0, (100 - security_score) // 3)  # Max 33%
        
        return {
            "revenue_loss_annual": revenue_loss,
            "seo_impact": seo_impact,
            "user_trust_impact": trust_impact
        }
    
    @staticmethod
    def generate_business_recommendations(
        ssl_result: Dict[str, Any], 
        issues: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate business-focused recommendations"""
        recommendations = []
        ssl_status = ssl_result.get('ssl_status', 'connection_error')
        
        if ssl_status == 'no_ssl' or not ssl_result.get('port_443_open', False):
            recommendations.extend([
                "긴급: SSL 인증서 설치 및 HTTPS 서비스 활성화 (오늘 실행)",
                "필수: Let's Encrypt 무료 SSL 적용 (투자 0원)",
                "권장: HTTP → HTTPS 자동 리다이렉션 설정 (이번 주)",
                "장기: 보안 모니터링 체계 구축 (1개월)"
            ])
        elif ssl_status == 'expired':
            recommendations.extend([
                "새로운 SSL 인증서를 즉시 발급하세요.",
                "Let's Encrypt 자동 갱신 시스템을 설정하세요."
            ])
        elif ssl_status == 'self_signed':
            recommendations.extend([
                "신뢰할 수 있는 인증기관(CA)에서 SSL 인증서를 발급받으세요.",
                "Let's Encrypt를 이용하여 무료로 인증서를 발급받을 수 있습니다."
            ])
        elif ssl_status == 'valid':
            recommendations.extend(
                BusinessImpactService._generate_valid_ssl_recommendations(ssl_result)
            )
        else:
            recommendations.append("서버 연결 문제를 해결한 후 SSL 인증서를 설치하세요.")
        
        return recommendations
    
    @staticmethod
    def _generate_valid_ssl_recommendations(ssl_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations for valid SSL certificates"""
        recommendations = []
        
        missing_headers = ssl_result.get("missing_security_headers", [])
        if missing_headers:
            recommendations.append("누락된 보안 헤더들을 웹서버 설정에 추가하세요.")
        
        ssl_grade = ssl_result.get("ssl_grade", "B")
        if ssl_grade in ["B", "C", "D"]:
            recommendations.append("SSL 등급 A 이상 달성을 위해 TLS 1.3 지원 및 보안 설정을 강화하세요.")
        
        days_until_expiry = ssl_result.get('days_until_expiry', 0)
        if 0 < days_until_expiry < 30:
            recommendations.append("인증서 만료가 임박했습니다. 자동 갱신 시스템을 확인하세요.")
        
        if not missing_headers and ssl_grade in ['A+', 'A', 'A-']:
            recommendations.append("현재 보안 설정이 우수합니다. 지속적인 모니터링을 권장합니다.")
        
        return recommendations
    
    @staticmethod
    def calculate_roi_analysis(business_impact: Dict[str, int]) -> Dict[str, Any]:
        """Calculate ROI analysis for security improvements"""
        annual_loss = business_impact.get('revenue_loss_annual', 0)
        
        # Estimated costs
        ssl_cost = 300000  # Annual SSL certificate cost estimate
        consulting_cost = 500000  # Basic consulting cost
        implementation_cost = 300000  # Basic implementation cost
        
        total_investment = ssl_cost + consulting_cost + implementation_cost
        
        # ROI calculation
        roi_ratio = annual_loss // total_investment if total_investment > 0 else 1
        payback_period_days = int((total_investment / annual_loss * 365)) if annual_loss > 0 else 365
        
        return {
            'investment_cost': total_investment,
            'annual_savings': annual_loss,
            'roi_ratio': roi_ratio,
            'payback_period_days': payback_period_days,
            'monthly_savings': annual_loss // 12 if annual_loss > 0 else 0
        }