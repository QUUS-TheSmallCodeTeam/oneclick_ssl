"""
TSC 보고서 형식의 전문적인 PDF 보고서 생성 모듈 (HTML to PDF 방식)
TSC_Website_Security_Analysis_Report.md 형식을 따름
"""

from typing import Dict, Any, List
from io import BytesIO
from datetime import datetime
from jinja2 import Template
import os

# WeasyPrint 제거됨 - 클라이언트 사이드 PDF 생성 사용


def convert_html_to_pdf(analysis_data: Dict[str, Any]) -> bytes:
    """클라이언트 사이드 PDF 생성을 위해 간단한 텍스트 보고서 반환"""  
    try:
        # 텍스트 보고서로 대체 (클라이언트에서 HTML->PDF 변환)
        text_content = _generate_tsc_text_report(analysis_data)
        return text_content.encode('utf-8')
            
    except Exception as e:
        print(f"보고서 생성 오류: {str(e)}")
        return "보고서 생성에 실패했습니다.".encode('utf-8')


def _generate_tsc_html_report(analysis_data: Dict[str, Any]) -> str:
    """분석 데이터로부터 TSC 형식의 HTML 보고서를 생성합니다."""
    try:
        template = Template(_get_tsc_html_template())
        
        # 템플릿에 전달할 데이터 확장
        template_data = {**analysis_data}
        template_data.update({
            "grade_color": _get_grade_color(analysis_data.get("ssl_grade", "F")),
            "score_color": _get_score_color(analysis_data.get("security_score", 0))
        })
        
        html_content = template.render(**template_data)
        return html_content
        
    except Exception as e:
        print(f"HTML 템플릿 렌더링 오류: {str(e)}")
        raise e


def _get_tsc_html_template() -> str:
    """TSC 형식의 HTML 템플릿 반환 (문자열 연결 제거)"""
    styles = _get_tsc_html_styles()
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{{{ domain }}}} 웹사이트 보안 분석 보고서</title>
    <style>{styles}</style>
</head>
<body>
    <button class="print-button" onclick="window.print()">🖨️ PDF 다운로드</button>
    
    <!-- TSC 보고서 헤더 -->
    <h1>{{{{ domain }}}} 웹사이트 보안 분석 보고서</h1>
    
    <div class="header-meta">
        <p><strong>분석 대상</strong>: {{{{ domain }}}}</p>
        <p><strong>분석 일시</strong>: {{{{ analysis_date }}}}</p>
        <p><strong>분석자</strong>: SecureCheck Pro Security Analysis Team</p>
        <p><strong>보고서 버전</strong>: 1.0</p>
    </div>
    
    <hr class="divider">

    <!-- Executive Summary -->
    <div class="section">
        <h2>📋 Executive Summary</h2>
        
        <h3>🚨 주요 발견사항</h3>
        <ul class="findings-list">
            <li>SSL 등급: {{{{ ssl_grade }}}}</li>
            <li>보안 점수: {{{{ security_score }}}}/100</li>
            <li>인증서 유효성: {{% if certificate_valid %}}유효{{% else %}}무효{{% endif %}}</li>
        </ul>
        
        <h3>💰 비즈니스 영향</h3>
        <ul class="business-impact-list">
            <li><strong>현재 보안 상태</strong>: 지속적인 보안 관리 필요</li>
            <li><strong>브랜드 신뢰도</strong>: 현재 수준 유지</li>
            <li><strong>법적 준수</strong>: 기본 요구사항 충족</li>
        </ul>
    </div>
    
</body>
</html>"""


def _get_tsc_html_styles() -> str:
    """TSC 보고서용 CSS 스타일"""
    return """
        /* A4 페이지 설정 */
        @page {
            size: A4;
            margin: 2.5cm;
        }
        
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: white;
            margin: 0;
            padding: 20px;
        }
        
        .print-button {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            z-index: 1000;
        }
        
        @media print {
            .print-button {
                display: none;
            }
        }
        
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        
        h2 {
            color: #34495e;
            margin-top: 30px;
        }
        
        .header-meta {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        
        .divider {
            border: none;
            border-top: 2px solid #e9ecef;
            margin: 30px 0;
        }
        
        .section {
            margin: 30px 0;
        }
        
        .findings-list, .business-impact-list {
            background: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #3498db;
            margin: 15px 0;
        }
        
        .findings-list li, .business-impact-list li {
            margin: 8px 0;
        }
    """


def _get_grade_color(ssl_grade: str) -> str:
    """SSL 등급에 따른 색상 반환"""
    colors = {
        'A': '#27ae60', 'A+': '#27ae60', 'A-': '#f39c12',
        'B': '#f39c12', 'C': '#e67e22', 'D': '#e74c3c', 'F': '#c0392b'
    }
    return colors.get(ssl_grade, '#c0392b')


def _get_score_color(score: int) -> str:
    """보안 점수에 따른 색상 반환"""
    if score >= 80:
        return '#27ae60'
    elif score >= 60:
        return '#f39c12'
    else:
        return '#e74c3c'


def _generate_tsc_text_report(analysis_data: Dict[str, Any]) -> str:
    """간단한 텍스트 보고서 생성"""
    domain = analysis_data.get('domain', 'Unknown')
    ssl_grade = analysis_data.get('ssl_grade', 'F')
    security_score = analysis_data.get('security_score', 0)
    
    return f"""
═══════════════════════════════════════════════════════════════
              {domain} 웹사이트 보안 분석 보고서
═══════════════════════════════════════════════════════════════

분석 대상: {domain}
분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
SSL 등급: {ssl_grade}
보안 점수: {security_score}/100

═══════════════════════════════════════════════════════════════
              SecureCheck Pro - 웹사이트 보안 전문가
═══════════════════════════════════════════════════════════════
    """


def _get_tsc_pdf_styles() -> str:
    """PDF 생성용 스타일 (WeasyPrint용)"""
    return _get_tsc_html_styles()