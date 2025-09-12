import os
import asyncio
from datetime import datetime
from jinja2 import Template
from typing import Dict, Any
import json

class ReportGenerator:
    """보고서 생성 클래스"""
    
    def __init__(self):
        self.reports_dir = "reports"
        # Fix path resolution to find templates in project root
        self.templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
        
        # 디렉토리 생성
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.templates_dir), exist_ok=True)
    
    async def generate_pdf_report(self, report_id: str, analysis_data: Dict[str, Any]) -> str:
        """PDF 보고서를 생성합니다."""
        try:
            # HTML 보고서 생성
            html_content = self._generate_html_report(analysis_data)
            
            # PDF 파일 경로
            pdf_path = os.path.join(self.reports_dir, f"{report_id}.pdf")
            
            # HTML을 PDF로 변환 (WeasyPrint 사용)
            try:
                from weasyprint import HTML, CSS
                from weasyprint.text.fonts import FontConfiguration
                
                # 폰트 설정
                font_config = FontConfiguration()
                
                HTML(string=html_content).write_pdf(
                    pdf_path,
                    font_config=font_config,
                    stylesheets=[CSS(string=self._get_pdf_styles())]
                )
                
            except ImportError:
                # WeasyPrint가 없는 경우 간단한 텍스트 파일로 대체
                text_content = self._generate_text_report(analysis_data)
                with open(pdf_path.replace('.pdf', '.txt'), 'w', encoding='utf-8') as f:
                    f.write(text_content)
                pdf_path = pdf_path.replace('.pdf', '.txt')
            
            return pdf_path
            
        except Exception as e:
            # 오류 발생시 간단한 텍스트 보고서라도 생성
            error_report = f"""
SecureCheck Pro 보안 분석 보고서
분석 대상: {analysis_data.get('url', 'Unknown')}
생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

오류가 발생하여 상세 보고서를 생성할 수 없습니다.
오류 내용: {str(e)}

기본 분석 결과:
- SSL 등급: {analysis_data.get('ssl_grade', 'Unknown')}
- 보안 점수: {analysis_data.get('security_score', 0)}/100
- 발견된 문제: {len(analysis_data.get('issues', []))}개
"""
            
            error_path = os.path.join(self.reports_dir, f"{report_id}_error.txt")
            with open(error_path, 'w', encoding='utf-8') as f:
                f.write(error_report)
            
            return error_path
    
    def _generate_html_report(self, data: Dict[str, Any]) -> str:
        """HTML 보고서 생성 (고급 템플릿 사용)"""
        from jinja2 import Environment, FileSystemLoader
        
        # Jinja2 환경 설정 (템플릿 상속 지원)
        try:
            env = Environment(loader=FileSystemLoader(self.templates_dir))
            template = env.get_template('comprehensive_report_template.html')
        except Exception as e:
            print(f"Advanced template loading failed: {e}")
            # 기본 템플릿으로 폴백
            template_path = os.path.join(self.templates_dir, "report_template.html")
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                template = Template(template_content)
            except FileNotFoundError:
                print(f"Template file not found at: {template_path}")
                print(f"Templates directory: {self.templates_dir}")
                print(f"Template directory exists: {os.path.exists(self.templates_dir)}")
                raise Exception(f"Template file not found: {template_path}")
        
        # 도메인 정보 추출
        url = data.get('url', data.get('domain', ''))
        if isinstance(url, str):
            domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        else:
            domain = str(url).replace('https://', '').replace('http://', '').split('/')[0]
        
        # 분석 날짜
        analysis_date = datetime.now().strftime('%Y년 %m월 %d일')
        report_date = datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')
        
        # SSL 등급에 따른 grade_class 설정
        ssl_grade = data.get('ssl_grade', 'F')
        grade_class = ssl_grade.lower().replace('+', 'plus').replace('-', 'minus')
        
        # 비즈니스 영향 데이터 준비
        business_impact = data.get('business_impact', {})
        if not business_impact.get('revenue_loss_annual'):
            # SSL 등급에 따른 기본 손실 추정
            base_loss = {
                'F': 100000000,  # 1억원
                'D': 50000000,   # 5천만원
                'C': 30000000,   # 3천만원
                'B': 10000000,   # 1천만원
                'A': 0,
                'A+': 0
            }
            business_impact['revenue_loss_annual'] = base_loss.get(ssl_grade, 50000000)
        
        # 템플릿에 전달할 데이터 준비
        template_data = {
            'report_title': 'SecureCheck Pro 보안 분석 보고서',
            'generated_at': report_date,
            'analysis_date': analysis_date,
            'report_date': report_date,
            'url': url,
            'domain': domain,
            'ssl_grade': ssl_grade,
            'grade_class': grade_class,
            'security_grade': ssl_grade,
            'security_score': data.get('security_score', 0),
            'issues': data.get('issues', []),
            'business_impact': business_impact,
            'recommendations': data.get('recommendations', []),
            'grade_color': self._get_grade_color(ssl_grade),
            'score_color': self._get_score_color(data.get('security_score', 0)),
            
            # 추가 SSL 분석 데이터
            'certificate_valid': data.get('certificate_valid', ssl_grade not in ['F']),
            'certificate_expired': data.get('certificate_expired', False),
            'days_until_expiry': data.get('days_until_expiry', 365),
            'missing_security_headers': data.get('missing_security_headers', []),
            'security_headers_present': data.get('security_headers_present', []),
            
            # Format currency helper
            'format_currency': lambda amount: f"₩{amount:,}" if isinstance(amount, (int, float)) else str(amount)
        }
        
        # Jinja2 필터 추가
        if hasattr(template.environment, 'filters'):
            template.environment.filters['format_currency'] = template_data['format_currency']
        
        return template.render(**template_data)
    
    def _generate_text_report(self, data: Dict[str, Any]) -> str:
        """텍스트 보고서 생성 (PDF 생성 실패시 대안)"""
        issues = data.get('issues', [])
        business_impact = data.get('business_impact', {})
        recommendations = data.get('recommendations', [])
        
        report = f"""
═══════════════════════════════════════════════════════════════
              SecureCheck Pro 보안 분석 보고서
═══════════════════════════════════════════════════════════════

📊 분석 개요
───────────────────────────────────────────────────────────────
• 분석 대상: {data.get('url', 'Unknown')}
• SSL 등급: {data.get('ssl_grade', 'F')}
• 보안 점수: {data.get('security_score', 0)}/100점
• 분석 완료: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}

💼 비즈니스 영향 분석
───────────────────────────────────────────────────────────────
• 예상 연간 매출 손실: ₩{business_impact.get('revenue_loss_annual', 0):,}
• SEO 순위 영향: -{business_impact.get('seo_impact', 0)}%
• 고객 신뢰도 영향: -{business_impact.get('user_trust_impact', 0)}%

🚨 발견된 보안 문제 ({len(issues)}개)
───────────────────────────────────────────────────────────────
"""
        
        if not issues:
            report += "• 심각한 보안 문제가 발견되지 않았습니다.\n\n"
        else:
            for i, issue in enumerate(issues, 1):
                severity_emoji = {
                    'critical': '🔴',
                    'high': '🟠', 
                    'medium': '🟡',
                    'low': '🟢'
                }.get(issue.get('severity', 'low'), '🔘')
                
                report += f"{severity_emoji} [{issue.get('severity', 'UNKNOWN').upper()}] {issue.get('title', '알 수 없는 문제')}\n"
                report += f"   {issue.get('description', '설명 없음')}\n\n"
        
        report += """🛠️ 개선 권장사항
───────────────────────────────────────────────────────────────
"""
        
        if not recommendations:
            report += "• 추가 권장사항이 없습니다.\n\n"
        else:
            for i, rec in enumerate(recommendations, 1):
                report += f"{i}. {rec}\n\n"
        
        report += """
═══════════════════════════════════════════════════════════════
              SecureCheck Pro - 웹사이트 보안 전문가
═══════════════════════════════════════════════════════════════
"""
        
        return report
    
    def _create_default_template(self):
        """기본 HTML 템플릿 생성"""
        template_path = os.path.join(self.templates_dir, "report_template.html")
        
        if os.path.exists(template_path):
            return
        
        template_content = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ report_title }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; text-align: center; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 2rem 0; }
        .summary-card { background: #f8f9fa; border-left: 4px solid #007bff; padding: 1rem; }
        .grade { font-size: 3rem; font-weight: bold; color: {{ grade_color }}; }
        .score { font-size: 2.5rem; font-weight: bold; color: {{ score_color }}; }
        .section { margin: 2rem 0; }
        .issue { border: 1px solid #dee2e6; border-radius: 8px; margin: 1rem 0; padding: 1rem; }
        .issue.critical { border-left: 4px solid #dc3545; background: #f8d7da; }
        .issue.high { border-left: 4px solid #fd7e14; background: #ffeaa7; }
        .issue.medium { border-left: 4px solid #ffc107; background: #fff3cd; }
        .issue.low { border-left: 4px solid #28a745; background: #d1e7dd; }
        .recommendations { background: #e7f3ff; border: 1px solid #0066cc; border-radius: 8px; padding: 1.5rem; }
        .footer { text-align: center; color: #6c757d; margin-top: 3rem; padding: 2rem; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ report_title }}</h1>
        <p>{{ url }}</p>
        <p>생성일시: {{ generated_at }}</p>
    </div>

    <div class="summary">
        <div class="summary-card">
            <h3>SSL 등급</h3>
            <div class="grade">{{ ssl_grade }}</div>
        </div>
        <div class="summary-card">
            <h3>보안 점수</h3>
            <div class="score">{{ security_score }}/100</div>
        </div>
        <div class="summary-card">
            <h3>발견된 문제</h3>
            <div style="font-size: 2rem; font-weight: bold;">{{ issues|length }}개</div>
        </div>
        <div class="summary-card">
            <h3>예상 연간 손실</h3>
            <div style="font-size: 1.5rem; font-weight: bold; color: #dc3545;">
                ₩{{ "{:,}".format(business_impact.revenue_loss_annual) }}
            </div>
        </div>
    </div>

    <div class="section">
        <h2>🚨 발견된 보안 문제</h2>
        {% if issues %}
            {% for issue in issues %}
            <div class="issue {{ issue.severity }}">
                <h3>{{ issue.title }} <span style="font-size: 0.8rem; opacity: 0.8;">[{{ issue.severity.upper() }}]</span></h3>
                <p>{{ issue.description }}</p>
            </div>
            {% endfor %}
        {% else %}
            <p>심각한 보안 문제가 발견되지 않았습니다.</p>
        {% endif %}
    </div>

    <div class="section">
        <h2>💼 비즈니스 영향</h2>
        <div class="summary">
            <div class="summary-card">
                <h4>연간 매출 손실</h4>
                <p style="color: #dc3545; font-weight: bold;">₩{{ "{:,}".format(business_impact.revenue_loss_annual) }}</p>
            </div>
            <div class="summary-card">
                <h4>SEO 순위 영향</h4>
                <p style="color: #fd7e14; font-weight: bold;">-{{ business_impact.seo_impact }}%</p>
            </div>
            <div class="summary-card">
                <h4>고객 신뢰도</h4>
                <p style="color: #dc3545; font-weight: bold;">-{{ business_impact.user_trust_impact }}%</p>
            </div>
        </div>
    </div>

    <div class="section recommendations">
        <h2>🛠️ 개선 권장사항</h2>
        {% if recommendations %}
            <ol>
            {% for rec in recommendations %}
                <li>{{ rec }}</li>
            {% endfor %}
            </ol>
        {% else %}
            <p>현재 상태가 양호합니다.</p>
        {% endif %}
    </div>

    <div class="footer">
        <p><strong>SecureCheck Pro</strong> - 웹사이트 보안 전문 분석 서비스</p>
        <p>본 보고서는 {{ generated_at }}에 자동 생성되었습니다.</p>
    </div>
</body>
</html>"""
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
    
    def _get_grade_color(self, grade: str) -> str:
        """SSL 등급에 따른 색상 반환"""
        colors = {
            'A+': '#28a745',
            'A': '#28a745', 
            'A-': '#28a745',
            'B': '#ffc107',
            'C': '#fd7e14',
            'D': '#dc3545',
            'F': '#dc3545'
        }
        return colors.get(grade, '#dc3545')
    
    def _get_score_color(self, score: int) -> str:
        """보안 점수에 따른 색상 반환"""
        if score >= 90:
            return '#28a745'
        elif score >= 70:
            return '#ffc107'
        elif score >= 50:
            return '#fd7e14'
        else:
            return '#dc3545'
    
    def _get_pdf_styles(self) -> str:
        """PDF 전용 CSS 스타일"""
        return """
        @page {
            margin: 2cm;
            @bottom-center {
                content: "SecureCheck Pro - 페이지 " counter(page);
                font-size: 10pt;
                color: #666;
            }
        }
        body {
            font-family: 'DejaVu Sans', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }
        """