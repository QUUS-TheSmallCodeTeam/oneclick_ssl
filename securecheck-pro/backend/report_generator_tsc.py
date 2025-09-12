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
    """TSC 형식의 전문적인 HTML 보고서 템플릿"""
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
    
    <!-- 보고서 헤더 -->
    <div class="report-header">
        <h1>{{{{ domain }}}} 웹사이트 보안 분석 보고서</h1>
        <div class="header-meta">
            <div class="meta-left">
                <p><strong>분석 대상</strong>: {{{{ domain }}}}</p>
                <p><strong>분석 일시</strong>: {{{{ analysis_date }}}}</p>
            </div>
            <div class="meta-right">
                <p><strong>분석 도구</strong>: SecureCheck Pro</p>
                <p><strong>보안 등급</strong>: <span class="grade-badge grade-{{{{ ssl_grade|lower }}}}">{{{{ ssl_grade }}}}</span></p>
            </div>
        </div>
    </div>

    <!-- 보안 점수 개요 -->
    <section class="security-overview page-break-avoid">
        <h2>📊 보안 점수 개요</h2>
        <div class="score-display">
            <div class="score-circle score-{{{{ 'good' if security_score >= 80 else 'medium' if security_score >= 60 else 'poor' }}}}">
                <div class="score-number">{{{{ security_score }}}}/100</div>
                <div class="score-label">보안 점수</div>
            </div>
        </div>
    </section>

    <!-- Executive Summary -->
    <section class="executive-summary page-break-avoid">
        <h2>📋 Executive Summary</h2>
        
        <div class="summary-content">
            {{{{ domain }}}} 웹사이트의 보안 분석 결과, 
            {{% if ssl_grade in ['F', 'D'] %}}
            <strong class="status-critical">보안에 심각한 취약점이 발견</strong>되었습니다. 즉시 개선이 필요한 상태입니다.
            {{% elif ssl_grade in ['C', 'B'] %}}
            <strong class="status-warning">기본적인 보안은 확보</strong>되어 있으나, 추가 보안 강화가 권장됩니다.
            {{% else %}}
            <strong class="status-good">양호한 보안 수준</strong>을 유지하고 있으나, 지속적인 모니터링이 필요합니다.
            {{% endif %}}
            이 보고서는 현재 보안 상태에 대한 종합적인 분석과 개선 방안을 제시합니다.
        </div>

        <h3>🚨 주요 발견사항</h3>
        <div class="findings-grid">
            <div class="finding-item">
                <span class="finding-icon">🔒</span>
                <div>
                    <strong>SSL 등급</strong><br>
                    <span class="grade-{{{{ ssl_grade|lower }}}}">{{{{ ssl_grade }}}} 등급</span>
                </div>
            </div>
            <div class="finding-item">
                <span class="finding-icon">📊</span>
                <div>
                    <strong>보안 점수</strong><br>
                    {{{{ security_score }}}}/100점
                </div>
            </div>
            <div class="finding-item">
                <span class="finding-icon">📜</span>
                <div>
                    <strong>인증서 상태</strong><br>
                    {{% if certificate_valid %}}유효{{% else %}}무효{{% endif %}}
                </div>
            </div>
            <div class="finding-item">
                <span class="finding-icon">⚠️</span>
                <div>
                    <strong>보안 헤더</strong><br>
                    {{{{ missing_headers|length }}}}개 누락
                </div>
            </div>
        </div>
    </section>

    <!-- 위험 요소 매트릭스 -->
    <section class="risk-matrix page-break-before">
        <h2>🔍 위험 요소 매트릭스</h2>
        <table class="risk-table">
            <thead>
                <tr>
                    <th>위험 요소</th>
                    <th>현재 상태</th>
                    <th>영향도</th>
                    <th>발생확률</th>
                    <th>종합 위험도</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>데이터 도청</strong></td>
                    <td class="status-{{% if ssl_grade in ['F', 'D'] %}}high{{% else %}}low{{% endif %}}">
                        {{% if ssl_grade in ['F', 'D'] %}}매우 높음{{% else %}}낮음{{% endif %}}
                    </td>
                    <td class="impact-critical">치명적</td>
                    <td class="prob-{{% if ssl_grade in ['F', 'D'] %}}certain{{% else %}}low{{% endif %}}">
                        {{% if ssl_grade in ['F', 'D'] %}}확실{{% else %}}낮음{{% endif %}}
                    </td>
                    <td class="risk-{{% if ssl_grade in ['F', 'D'] %}}critical{{% else %}}low{{% endif %}}">
                        {{% if ssl_grade in ['F', 'D'] %}}🔴 Critical{{% else %}}🟢 Low{{% endif %}}
                    </td>
                </tr>
                <tr>
                    <td><strong>중간자 공격 (MITM)</strong></td>
                    <td class="status-{{% if ssl_grade in ['F', 'D'] %}}high{{% else %}}medium{{% endif %}}">
                        {{% if ssl_grade in ['F', 'D'] %}}매우 높음{{% else %}}보통{{% endif %}}
                    </td>
                    <td class="impact-critical">치명적</td>
                    <td class="prob-{{% if ssl_grade in ['F', 'D'] %}}high{{% else %}}medium{{% endif %}}">
                        {{% if ssl_grade in ['F', 'D'] %}}높음{{% else %}}보통{{% endif %}}
                    </td>
                    <td class="risk-{{% if ssl_grade in ['F', 'D'] %}}critical{{% else %}}medium{{% endif %}}">
                        {{% if ssl_grade in ['F', 'D'] %}}🔴 Critical{{% else %}}🟡 Medium{{% endif %}}
                    </td>
                </tr>
                <tr>
                    <td><strong>브랜드 손상</strong></td>
                    <td class="status-{{% if ssl_grade in ['F', 'D', 'C'] %}}high{{% else %}}low{{% endif %}}">
                        {{% if ssl_grade in ['F', 'D', 'C'] %}}현재 발생{{% else %}}낮음{{% endif %}}
                    </td>
                    <td class="impact-high">높음</td>
                    <td class="prob-{{% if ssl_grade in ['F', 'D', 'C'] %}}certain{{% else %}}low{{% endif %}}">
                        {{% if ssl_grade in ['F', 'D', 'C'] %}}확실{{% else %}}낮음{{% endif %}}
                    </td>
                    <td class="risk-{{% if ssl_grade in ['F', 'D', 'C'] %}}high{{% else %}}low{{% endif %}}">
                        {{% if ssl_grade in ['F', 'D', 'C'] %}}🟡 High{{% else %}}🟢 Low{{% endif %}}
                    </td>
                </tr>
            </tbody>
        </table>
    </section>

    <!-- 비즈니스 영향 분석 -->
    <section class="business-impact page-break-avoid">
        <h2>💰 비즈니스 영향 분석</h2>
        
        <div class="impact-grid">
            <div class="impact-card impact-revenue">
                <h3>📉 매출 영향</h3>
                <div class="impact-value">
                    {{% set revenue_loss = (100 - security_score) * 1000000 %}}
                    ₩{{{{ "{:,}".format(revenue_loss) }}}}
                </div>
                <p class="impact-desc">예상 연간 기회비용 손실</p>
            </div>
            
            <div class="impact-card impact-trust">
                <h3>👥 사용자 신뢰도</h3>
                <div class="impact-value">
                    {{% if ssl_grade in ['F', 'D'] %}}
                    -70%
                    {{% elif ssl_grade in ['C', 'B'] %}}
                    -30%
                    {{% else %}}
                    +10%
                    {{% endif %}}
                </div>
                <p class="impact-desc">브라우저 보안 경고 영향</p>
            </div>
            
            <div class="impact-card impact-seo">
                <h3>🔍 SEO 순위</h3>
                <div class="impact-value">
                    {{% if ssl_grade in ['F', 'D'] %}}
                    -40%
                    {{% elif ssl_grade in ['C', 'B'] %}}
                    -15%
                    {{% else %}}
                    유지
                    {{% endif %}}
                </div>
                <p class="impact-desc">Google 검색 순위 변화</p>
            </div>
        </div>
    </section>

    <!-- 개선 권장사항 -->
    <section class="recommendations page-break-before">
        <h2>🛠️ 즉시 권장 조치</h2>
        
        <div class="recommendations-list">
            {{% if ssl_grade in ['F', 'D'] %}}
            <div class="recommendation urgent">
                <div class="rec-priority">🔥 긴급</div>
                <div class="rec-content">
                    <h3>SSL 인증서 설치 및 HTTPS 서비스 활성화</h3>
                    <p>Let's Encrypt 무료 SSL 적용 (투자 0원, 당일 완료 가능)</p>
                </div>
            </div>
            <div class="recommendation high">
                <div class="rec-priority">⚡ 필수</div>
                <div class="rec-content">
                    <h3>HTTP → HTTPS 자동 리다이렉션 설정</h3>
                    <p>모든 HTTP 접속을 HTTPS로 자동 전환하여 보안 경고 완전 제거</p>
                </div>
            </div>
            {{% elif ssl_grade in ['C', 'B'] %}}
            <div class="recommendation high">
                <div class="rec-priority">📈 중요</div>
                <div class="rec-content">
                    <h3>SSL 보안 설정 강화</h3>
                    <p>TLS 1.3 적용 및 보안 헤더 설정으로 A 등급 달성</p>
                </div>
            </div>
            {{% endif %}}
            
            {{% if missing_headers|length > 0 %}}
            <div class="recommendation medium">
                <div class="rec-priority">🔒 권장</div>
                <div class="rec-content">
                    <h3>보안 헤더 설정</h3>
                    <p>누락된 {{{{ missing_headers|length }}}}개 보안 헤더 추가: 
                    {{% for header in missing_headers[:3] %}}
                    {{{{ header }}}}{{% if not loop.last %}, {{% endif %}}
                    {{% endfor %}}
                    {{% if missing_headers|length > 3 %}} 외 {{{{ missing_headers|length - 3 }}}}개{{% endif %}}</p>
                </div>
            </div>
            {{% endif %}}
            
            <div class="recommendation normal">
                <div class="rec-priority">📊 장기</div>
                <div class="rec-content">
                    <h3>보안 모니터링 체계 구축</h3>
                    <p>자동 SSL 갱신 및 정기 보안 점검 시스템 구축</p>
                </div>
            </div>
        </div>
    </section>

    <!-- 푸터 -->
    <footer class="report-footer">
        <p>본 보고서는 SecureCheck Pro에 의해 자동 생성되었습니다 | 생성일시: {{{{ analysis_date }}}}</p>
        <p>⚠️ 이 보고서는 분석 시점 기준이며, 웹사이트 변경시 재분석이 필요합니다</p>
    </footer>
    
</body>
</html>"""


def _get_tsc_html_styles() -> str:
    """TSC 보고서용 전문적인 CSS 스타일"""
    return """
        /* A4 페이지 설정 */
        @page {
            size: A4;
            margin: 2cm;
        }
        
        /* 기본 스타일 */
        body {
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            color: #333;
            background: white;
            margin: 0;
            padding: 20px;
            font-size: 12px;
        }
        
        /* 인쇄 버튼 */
        .print-button {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #007bff;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            z-index: 1000;
            box-shadow: 0 2px 8px rgba(0,123,255,0.3);
        }
        
        .print-button:hover {
            background: #0056b3;
            transform: translateY(-1px);
        }
        
        /* 인쇄시 버튼 숨김 */
        @media print {
            .print-button { display: none; }
            body { font-size: 11px; }
        }
        
        /* 페이지 브레이크 */
        .page-break-before { page-break-before: always; }
        .page-break-avoid { page-break-inside: avoid; }
        
        /* 보고서 헤더 */
        .report-header {
            border-bottom: 3px solid #007bff;
            margin-bottom: 30px;
            padding-bottom: 20px;
        }
        
        .report-header h1 {
            color: #007bff;
            font-size: 24px;
            margin-bottom: 15px;
            font-weight: bold;
        }
        
        .header-meta {
            display: flex;
            justify-content: space-between;
            gap: 20px;
            margin-top: 15px;
        }
        
        .meta-left p, .meta-right p {
            margin: 5px 0;
            font-size: 12px;
            color: #666;
        }
        
        /* 등급 배지 */
        .grade-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: bold;
            color: white;
        }
        
        .grade-a, .grade-aplus { background-color: #28a745; }
        .grade-aminus, .grade-b { background-color: #ffc107; color: #000; }
        .grade-c { background-color: #fd7e14; }
        .grade-d, .grade-f { background-color: #dc3545; }
        
        /* 섹션 헤더 */
        section {
            margin-bottom: 40px;
        }
        
        section h2 {
            color: #007bff;
            font-size: 18px;
            margin-bottom: 20px;
            border-left: 4px solid #007bff;
            padding-left: 15px;
            font-weight: bold;
        }
        
        section h3 {
            color: #495057;
            font-size: 16px;
            margin-bottom: 15px;
            font-weight: bold;
        }
        
        /* 보안 점수 표시 */
        .score-display {
            display: flex;
            justify-content: center;
            margin: 30px 0;
        }
        
        .score-circle {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            border: 8px solid;
        }
        
        .score-good { 
            border-color: #28a745; 
            background: rgba(40, 167, 69, 0.1);
        }
        .score-medium { 
            border-color: #ffc107; 
            background: rgba(255, 193, 7, 0.1);
        }
        .score-poor { 
            border-color: #dc3545; 
            background: rgba(220, 53, 69, 0.1);
        }
        
        .score-number {
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }
        
        .score-label {
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }
        
        /* Executive Summary */
        .summary-content {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #007bff;
        }
        
        .status-critical { color: #dc3545; font-weight: bold; }
        .status-warning { color: #fd7e14; font-weight: bold; }
        .status-good { color: #28a745; font-weight: bold; }
        
        .findings-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 20px 0;
        }
        
        .finding-item {
            display: flex;
            align-items: center;
            padding: 15px;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            background: white;
        }
        
        .finding-icon {
            font-size: 24px;
            margin-right: 15px;
        }
        
        /* 위험 매트릭스 테이블 */
        .risk-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 11px;
        }
        
        .risk-table th, .risk-table td {
            padding: 12px 8px;
            text-align: center;
            border: 1px solid #dee2e6;
        }
        
        .risk-table th {
            background: #f8f9fa;
            font-weight: bold;
            color: #495057;
        }
        
        /* 위험도 컬러 코딩 */
        .status-high { background-color: #ffebee; color: #c62828; }
        .status-medium { background-color: #fff3e0; color: #ef6c00; }
        .status-low { background-color: #e8f5e8; color: #2e7d32; }
        
        .impact-critical { background-color: #ffebee; color: #c62828; font-weight: bold; }
        .impact-high { background-color: #fff3e0; color: #ef6c00; font-weight: bold; }
        
        .prob-certain { background-color: #ffebee; color: #c62828; }
        .prob-high { background-color: #fff3e0; color: #ef6c00; }
        .prob-medium { background-color: #fffde7; color: #f57f17; }
        .prob-low { background-color: #e8f5e8; color: #2e7d32; }
        
        .risk-critical { background-color: #ffcdd2; color: #b71c1c; font-weight: bold; }
        .risk-high { background-color: #ffe0b2; color: #e65100; font-weight: bold; }
        .risk-medium { background-color: #fff9c4; color: #f57f17; font-weight: bold; }
        .risk-low { background-color: #c8e6c9; color: #1b5e20; font-weight: bold; }
        
        /* 비즈니스 영향 카드 */
        .impact-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin: 20px 0;
        }
        
        .impact-card {
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #dee2e6;
        }
        
        .impact-revenue {
            background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
            border-color: #ef5350;
        }
        
        .impact-trust {
            background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
            border-color: #ff9800;
        }
        
        .impact-seo {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            border-color: #2196f3;
        }
        
        .impact-card h3 {
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #495057;
        }
        
        .impact-value {
            font-size: 20px;
            font-weight: bold;
            color: #333;
            margin: 10px 0;
        }
        
        .impact-desc {
            font-size: 11px;
            color: #666;
            margin: 0;
        }
        
        /* 권장사항 */
        .recommendations-list {
            margin: 20px 0;
        }
        
        .recommendation {
            display: flex;
            margin: 15px 0;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid;
        }
        
        .recommendation.urgent {
            border-color: #dc3545;
            background: rgba(220, 53, 69, 0.05);
        }
        
        .recommendation.high {
            border-color: #fd7e14;
            background: rgba(253, 126, 20, 0.05);
        }
        
        .recommendation.medium {
            border-color: #ffc107;
            background: rgba(255, 193, 7, 0.05);
        }
        
        .recommendation.normal {
            border-color: #28a745;
            background: rgba(40, 167, 69, 0.05);
        }
        
        .rec-priority {
            min-width: 70px;
            font-weight: bold;
            font-size: 12px;
            margin-right: 15px;
        }
        
        .rec-content h3 {
            margin: 0 0 8px 0;
            font-size: 14px;
            color: #333;
        }
        
        .rec-content p {
            margin: 0;
            font-size: 12px;
            color: #666;
        }
        
        /* 푸터 */
        .report-footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 10px;
            color: #666;
            text-align: center;
        }
        
        .report-footer p {
            margin: 5px 0;
        }
        
        /* 등급별 색상 */
        .grade-a, .grade-aplus { color: #28a745; }
        .grade-aminus { color: #ffc107; }
        .grade-b { color: #ffc107; }
        .grade-c { color: #fd7e14; }
        .grade-d, .grade-f { color: #dc3545; }
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