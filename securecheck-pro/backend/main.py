from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import uuid
import asyncio
from datetime import datetime

from ssl_analyzer import SSLAnalyzer
from typing import Dict, Any
from report_generator_tsc import create_tsc_style_pdf_report

# 분석 결과를 저장할 메모리 저장소 (실제로는 데이터베이스를 사용해야 함)
analysis_results = {}

def _generate_issues_from_ssl_result(ssl_result: Dict[str, Any]) -> List[Dict[str, str]]:
    """SSL 결과에서 이슈 목록 생성"""
    issues = []
    
    # 인증서 만료 임박
    days_until_expiry = ssl_result.get("days_until_expiry", 0)
    if days_until_expiry < 30:
        issues.append({
            "title": "SSL 인증서 만료 임박",
            "description": f"인증서가 {days_until_expiry}일 후 만료됩니다. 갱신이 필요합니다.",
            "severity": "high" if days_until_expiry < 7 else "medium"
        })
    
    # 인증서 유효성
    if not ssl_result.get("certificate_valid", True):
        issues.append({
            "title": "유효하지 않은 SSL 인증서",
            "description": "SSL 인증서가 유효하지 않습니다. 인증서를 확인하고 교체하세요.",
            "severity": "critical"
        })
    
    # 자체 서명 인증서
    if ssl_result.get("is_self_signed", False):
        issues.append({
            "title": "자체 서명 인증서 사용",
            "description": "자체 서명된 인증서를 사용하고 있습니다. 신뢰할 수 있는 CA에서 발급받은 인증서로 교체하세요.",
            "severity": "high"
        })
    
    # 보안 헤더 누락
    missing_headers = ssl_result.get("missing_security_headers", [])
    if missing_headers:
        critical_headers = ["Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options"]
        critical_missing = [h for h in missing_headers if h in critical_headers]
        
        if critical_missing:
            issues.append({
                "title": "중요 보안 헤더 누락",
                "description": f"다음 중요 보안 헤더가 누락되었습니다: {', '.join(critical_missing)}",
                "severity": "high"
            })
        
        if len(missing_headers) > len(critical_missing):
            other_missing = [h for h in missing_headers if h not in critical_headers]
            issues.append({
                "title": "보안 헤더 누락",
                "description": f"다음 보안 헤더가 누락되었습니다: {', '.join(other_missing)}",
                "severity": "medium"
            })
    
    # HSTS 비활성화
    if not ssl_result.get("hsts_enabled", False):
        issues.append({
            "title": "HSTS (HTTP Strict Transport Security) 비활성화",
            "description": "HSTS 헤더가 설정되지 않아 중간자 공격에 취약할 수 있습니다.",
            "severity": "medium"
        })
    
    return issues

def _generate_recommendations_from_ssl_result(ssl_result: Dict[str, Any]) -> List[str]:
    """SSL 결과에서 권장사항 생성"""
    recommendations = []
    
    # SSL 등급 기반 권장사항
    ssl_grade = ssl_result.get("ssl_grade", "F")
    if ssl_grade in ["F", "D", "C"]:
        recommendations.append("SSL 구성을 전면적으로 검토하고 최신 보안 프로토콜을 적용하세요.")
        recommendations.append("약한 암호화 스위트를 비활성화하고 강력한 암호화를 사용하세요.")
    elif ssl_grade == "B":
        recommendations.append("SSL 구성을 개선하여 A 등급을 목표로 하세요.")
    
    # 보안 헤더 권장사항
    missing_headers = ssl_result.get("missing_security_headers", [])
    if "Strict-Transport-Security" in missing_headers:
        recommendations.append("HSTS (HTTP Strict Transport Security) 헤더를 설정하여 HTTPS 연결을 강제하세요.")
    if "Content-Security-Policy" in missing_headers:
        recommendations.append("CSP (Content Security Policy) 헤더를 설정하여 XSS 공격을 방지하세요.")
    if "X-Frame-Options" in missing_headers:
        recommendations.append("X-Frame-Options 헤더를 설정하여 클릭재킹 공격을 방지하세요.")
    
    # 인증서 만료 권장사항
    days_until_expiry = ssl_result.get("days_until_expiry", 0)
    if days_until_expiry < 60:
        recommendations.append("SSL 인증서 자동 갱신 시스템을 구축하여 만료를 방지하세요.")
    
    # 기본 권장사항
    if not recommendations:
        recommendations.append("정기적인 보안 점검을 통해 보안 상태를 유지하세요.")
        recommendations.append("보안 헤더 및 SSL 구성을 주기적으로 모니터링하세요.")
    
    return recommendations

app = FastAPI(
    title="원클릭 SSL체크 API",
    description="웹사이트 SSL/TLS 보안을 원클릭으로 분석하고 보고서를 생성하는 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Hugging Face deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
import os
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
if os.path.exists("public"):
    app.mount("/public", StaticFiles(directory="public"), name="public")

# 요청/응답 모델
class AnalyzeRequest(BaseModel):
    url: HttpUrl

class SecurityIssue(BaseModel):
    type: str
    severity: str
    title: str
    description: str

class BusinessImpact(BaseModel):
    revenue_loss_annual: int
    seo_impact: int
    user_trust_impact: int

class AnalyzeResponse(BaseModel):
    id: str
    url: str
    ssl_grade: str
    security_score: int
    issues: List[SecurityIssue]
    business_impact: BusinessImpact
    recommendations: List[str]
    created_at: str

# 전역 인스턴스
ssl_analyzer = SSLAnalyzer()
# report_generator = ReportGenerator()

@app.get("/")
async def root():
    """Serve the main HTML file"""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "원클릭 SSL체크 API", "version": "1.0.0"}

@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_website(request: AnalyzeRequest):
    """웹사이트 보안 분석을 수행합니다."""
    try:
        url = str(request.url)
        analysis_id = str(uuid.uuid4())
        
        # 실제 SSL 분석 수행
        ssl_result = await ssl_analyzer.analyze(url)
        
        # 보안 점수 계산
        security_score = calculate_security_score(ssl_result)
        
        # 문제점 추출
        issues = extract_issues(ssl_result)
        
        # 비즈니스 영향 계산
        business_impact = calculate_business_impact(security_score, ssl_result, issues)
        
        # 개선 권장사항 생성
        recommendations = generate_recommendations(ssl_result, issues)
        
        # 응답 데이터 구성
        response_data = {
            "id": analysis_id,
            "url": url,
            "ssl_grade": ssl_result.get("ssl_grade", "F"),
            "security_score": security_score,
            "issues": issues,
            "business_impact": business_impact,
            "recommendations": recommendations,
            "created_at": datetime.now().isoformat(),
            "ssl_result": ssl_result  # PDF 생성을 위한 원본 SSL 결과 포함
        }

        # 분석 결과를 메모리에 저장 (실제로는 데이터베이스에 저장)
        analysis_results[analysis_id] = response_data
        print(f"분석 결과 저장됨: {analysis_id} - {url}")

        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류 발생: {str(e)}")

@app.get("/api/v1/reports/{report_id}/download")
async def download_report(report_id: str):
    """MD 디자인 요소가 적용된 PDF 보고서를 다운로드합니다."""
    print(f"PDF 다운로드 요청: {report_id}")  # 디버그 로그

    try:
        # 저장된 분석 결과 조회
        if report_id not in analysis_results:
            raise HTTPException(status_code=404, detail=f"분석 결과가 존재하지 않습니다: {report_id}")

        saved_result = analysis_results[report_id]
        ssl_result = saved_result.get("ssl_result", {})

        # PDF용 데이터 구성 - 실제 분석 결과 형식에 맞춤
        analysis_data = {
            "domain": ssl_result.get("domain", saved_result.get("url", "").replace("https://", "").replace("http://", "")),
            "analysis_date": ssl_result.get("analyzed_at", saved_result.get("created_at", datetime.now().isoformat())),
            "security_grade": ssl_result.get("ssl_grade", "F"),
            "security_score": int((ssl_result.get("headers_score", 0) + (90 if ssl_result.get("ssl_grade") in ['A+', 'A', 'A-'] else 70 if ssl_result.get("ssl_grade") == 'B' else 50)) / 2),
            "alert_message": f"SSL 상태: {ssl_result.get('ssl_status', 'unknown')} - 등급: {ssl_result.get('ssl_grade', 'F')}",
            "ssl_result": ssl_result,  # 전체 SSL 결과 포함
            "certificate_valid": ssl_result.get("certificate_valid", False),
            "days_until_expiry": ssl_result.get("days_until_expiry", 0),
            "missing_security_headers": ssl_result.get("missing_security_headers", []),
            "security_headers_present": ssl_result.get("security_headers_present", []),
            "issues": _generate_issues_from_ssl_result(ssl_result),
            "recommendations": _generate_recommendations_from_ssl_result(ssl_result),
            "user_loss_rate": saved_result.get("business_impact", {}).get("revenue_loss_annual", 0) / 10000000,
            "annual_loss": saved_result.get("business_impact", {}).get("revenue_loss_annual", 0),
            "seo_impact": saved_result.get("business_impact", {}).get("seo_impact", 0),
            "trust_damage": saved_result.get("business_impact", {}).get("user_trust_impact", 0),
            "conclusion_summary": f"SSL 등급: {ssl_result.get('ssl_grade', 'F')} - {len(ssl_result.get('missing_security_headers', []))}개의 보안 헤더 누락"
        }

        print("PDF 생성 시작...")  # 디버그 로그
        print(f"분석 데이터 키: {list(analysis_data.keys())}")  # 디버그 로그
        pdf_bytes = create_tsc_style_pdf_report(analysis_data)
        print(f"PDF 생성 완료: {len(pdf_bytes)} bytes")  # 디버그 로그

        def iter_pdf():
            yield pdf_bytes

        filename = f"{analysis_data.get('domain', 'report')}_security_report.pdf"
        print(f"파일명: {filename}")  # 디버그 로그

        response = StreamingResponse(
            iter_pdf(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        print("StreamingResponse 생성 완료")  # 디버그 로그
        return response

    except Exception as e:
        # 상세한 오류 로깅
        import traceback
        error_details = traceback.format_exc()
        print(f"PDF 생성 오류: {str(e)}")
        print(f"상세 오류: {error_details}")

        # 오류 응답 반환
        return {"error": f"PDF 생성 중 오류가 발생했습니다: {str(e)}"}

@app.post("/api/v1/reports/generate-pdf")
async def generate_pdf_report(request: dict):
    """PDF 보고서를 생성합니다 (별도 엔드포인트)."""
    try:
        analysis_data = request.get("analysis_data", {})
        pdf_bytes = create_tsc_style_pdf_report(analysis_data)

        return {
            "success": True,
            "pdf_size": len(pdf_bytes),
            "filename": f"{analysis_data.get('domain', 'report')}_security_report.pdf"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def calculate_security_score(ssl_result: dict) -> int:
    """실제 SSL 분석 결과를 바탕으로 보안 점수를 계산합니다 (TSC 보고서 기준)."""
    
    # SSL 상태에 따른 기본 점수
    ssl_status = ssl_result.get('ssl_status', 'connection_error')
    
    if ssl_status == 'no_ssl' or not ssl_result.get('port_443_open', False):
        # TSC 보고서: SSL 서비스 완전 부재
        return 0
    elif ssl_status == 'expired':
        return 10  # 만료된 인증서
    elif ssl_status == 'self_signed':
        return 25  # 자체 서명 인증서
    elif ssl_status == 'verify_failed':
        return 30  # 인증서 검증 실패
    elif ssl_status == 'valid':
        # 정상 SSL 인증서의 경우 등급에 따른 점수
        ssl_grade = ssl_result.get("ssl_grade", "B")
        grade_scores = {"A+": 95, "A": 90, "A-": 85, "B": 75, "C": 60, "D": 40}
        score = grade_scores.get(ssl_grade, 40)
        
        # 보안 헤더 상태 반영
        missing_headers = ssl_result.get("missing_security_headers", [])
        score -= len(missing_headers) * 3
        
        # 인증서 만료 임박도
        days_until_expiry = ssl_result.get('days_until_expiry', 0)
        if days_until_expiry < 30:
            score -= 10
        
        return max(0, score)
    else:
        return 0  # 연결 오류

def extract_issues(ssl_result: dict) -> List[dict]:
    """SSL 분석 결과에서 보안 문제를 추출합니다 (TSC 보고서 기준)."""
    print(ssl_result)
    issues = []
    
    ssl_status = ssl_result.get('ssl_status', 'connection_error')
    
    # 1. SSL 서비스 완전 부재 (TSC 보고서 주요 문제)
    if ssl_status == 'no_ssl' or not ssl_result.get('port_443_open', False):
        issues.append({
            "type": "ssl_service",
            "severity": "critical",
            "title": "HTTPS 서비스 완전 부재",
            "description": "443 포트가 닫혀있어 HTTPS 서비스가 전혀 제공되지 않습니다."
        })
        issues.append({
            "type": "data_encryption",
            "severity": "critical",
            "title": "모든 데이터 평문 전송",
            "description": "암호화 없이 모든 데이터가 평문으로 전송되어 도청 위험에 노출됩니다."
        })
        issues.append({
            "type": "browser_warning",
            "severity": "high",
            "title": "브라우저 보안 경고",
            "description": "모든 브라우저에서 '안전하지 않음' 경고 메시지가 표시됩니다."
        })
    
    # 2. 만료된 인증서
    if ssl_status == 'expired':
        issues.append({
            "type": "certificate",
            "severity": "critical",
            "title": "SSL 인증서 만료",
            "description": "SSL 인증서가 만료되어 브라우저에서 보안 경고를 표시합니다."
        })
    
    # 3. 자체 서명 인증서
    if ssl_status == 'self_signed':
        issues.append({
            "type": "certificate",
            "severity": "high",
            "title": "자체 서명 인증서",
            "description": "신뢰할 수 있는 인증기관에서 발급하지 않은 인증서로, 브라우저에서 경고를 표시합니다."
        })

    # 4. 인증서 검증 실패
    if ssl_status == 'verify_failed':
        issues.append({
            "type": "certificate",
            "severity": "critical",
            "title": "SSL 인증서 검증 실패",
            "description": "브라우저에서 SSL 인증서를 신뢰할 수 없습니다. 인증 기관이 유효하지 않거나 체인이 불완전합니다."
        })

    # 5. 보안 헤더 누락 (정상 SSL인 경우에도 체크)
    missing_headers = ssl_result.get("missing_security_headers", [])
    for header in missing_headers:
        issues.append({
            "type": "security_header",
            "severity": "medium",
            "title": f"{header} 헤더 누락",
            "description": f"{header} 보안 헤더가 설정되지 않았습니다."
        })
    
    # 5. 인증서 만료 임박 (정상 SSL인 경우에만 체크)
    if ssl_status == 'valid':
        days_until_expiry = ssl_result.get('days_until_expiry', 0)
        if 0 < days_until_expiry < 30:
            issues.append({
                "type": "certificate",
                "severity": "medium",
                "title": "SSL 인증서 만료 임박",
                "description": f"SSL 인증서가 {days_until_expiry}일 후에 만료됩니다."
            })
    
    return issues

def calculate_business_impact(security_score: int, ssl_result: dict, issues: List[dict]) -> dict:
    """보안 점수와 SSL 분석 결과를 바탕으로 비즈니스 영향을 계산합니다 (TSC 보고서 기준)."""
    
    ssl_status = ssl_result.get('ssl_status', 'connection_error')
    
    # TSC 보고서를 참고한 비즈니스 영향 계산
    if ssl_status == 'no_ssl' or not ssl_result.get('port_443_open', False):
        # SSL 서비스 완전 부재 - TSC 보고서 수치 사용
        return {
            "revenue_loss_annual": 1_008_000_000,  # TSC: 10.08억원
            "seo_impact": 35,  # 30-40% 하락 (보고서 기준)
            "user_trust_impact": 80  # 70-90% 이탈률 (보고서 기준)
        }
    
    elif ssl_status == 'expired':
        # 만료된 SSL 인증서
        return {
            "revenue_loss_annual": 600_000_000,  # 6억원
            "seo_impact": 25,
            "user_trust_impact": 70
        }
    
    elif ssl_status == 'self_signed':
        # 자체 서명 인증서
        return {
            "revenue_loss_annual": 400_000_000,  # 4억원
            "seo_impact": 20,
            "user_trust_impact": 60
        }
    
    elif ssl_status == 'valid':
        # 정상 SSL - 보안 점수에 따른 세분화된 영향
        base_revenue = 1_000_000_000
        loss_rate = max(0, (100 - security_score) / 100 * 0.15)  # 최대 15% 손실
        revenue_loss = int(base_revenue * loss_rate)
        
        seo_impact = max(0, (100 - security_score) // 15)  # 최대 6% 하락
        user_trust_impact = max(0, (100 - security_score) // 3)  # 최대 33% 영향
        
        return {
            "revenue_loss_annual": revenue_loss,
            "seo_impact": seo_impact,
            "user_trust_impact": user_trust_impact
        }
    
    else:
        # 연결 오류 등
        return {
            "revenue_loss_annual": 800_000_000,  # 8억원
            "seo_impact": 30,
            "user_trust_impact": 75
        }

def generate_recommendations(ssl_result: dict, issues: List[dict]) -> List[str]:
    """분석 결과를 바탕으로 개선 권장사항을 생성합니다 (TSC 보고서 기준)."""
    recommendations = []
    
    ssl_status = ssl_result.get('ssl_status', 'connection_error')
    
    if ssl_status == 'no_ssl' or not ssl_result.get('port_443_open', False):
        # TSC 보고서의 주요 권장사항
        recommendations.append("긴급: SSL 인증서 설치 및 HTTPS 서비스 활성화 (오늘 실행)")
        recommendations.append("필수: Let's Encrypt 무료 SSL 적용 (투자 0원)")
        recommendations.append("권장: HTTP → HTTPS 자동 리다이렉션 설정 (이번 주)")
        recommendations.append("장기: 보안 모니터링 체계 구축 (1개월)")
    
    elif ssl_status == 'expired':
        recommendations.append("새로운 SSL 인증서를 즉시 발급하세요.")
        recommendations.append("Let's Encrypt 자동 갱신 시스템을 설정하세요.")
    
    elif ssl_status == 'self_signed':
        recommendations.append("신뢰할 수 있는 인증기관(CA)에서 SSL 인증서를 발급받으세요.")
        recommendations.append("Let's Encrypt를 이용하여 무료로 인증서를 발급받을 수 있습니다.")
    
    elif ssl_status == 'valid':
        # 정상 SSL인 경우 세부 개선사항
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
    
    else:
        recommendations.append("서버 연결 문제를 해결한 후 SSL 인증서를 설치하세요.")
    
    return recommendations

# 이전 PDF 생성 함수는 report_generator_tsc.py로 이동됨

def create_basic_pdf() -> bytes:
    """PRD 명세에 따른 전문적 보안 분석 보고서 생성 (4섹션 구조)"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=50, leftMargin=50, 
                              topMargin=50, bottomMargin=50)
        
        # 스타일 정의
        styles = getSampleStyleSheet()
        
        # 전문적 스타일 정의
        title_style = ParagraphStyle(
            'ProfessionalTitle',
            parent=styles['Title'],
            fontSize=20,
            spaceAfter=30,
            textColor=colors.HexColor('#2c3e50'),
            alignment=1  # CENTER
        )
        
        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=15,
            spaceBefore=25,
            textColor=colors.HexColor('#34495e'),
            borderWidth=2,
            borderColor=colors.HexColor('#3498db'),
            borderPadding=8
        )
        
        subsection_heading = ParagraphStyle(
            'SubsectionHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            textColor=colors.HexColor('#7f8c8d')
        )
        
        normal_text = ParagraphStyle(
            'NormalText',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            spaceAfter=8,
            textColor=colors.HexColor('#2c3e50')
        )
        
        code_style = ParagraphStyle(
            'CodeStyle',
            parent=styles['Code'],
            fontSize=9,
            backColor=colors.HexColor('#f8f9fa'),
            borderColor=colors.HexColor('#dee2e6'),
            borderWidth=1,
            borderPadding=8,
            fontName='Courier'
        )

        story = []
        
        # 기본 데이터 추출
        domain = analysis_data.get('domain', 'Unknown Domain')
        ssl_result = analysis_data.get('ssl_result', {})
        security_score = analysis_data.get('security_score', 0)
        ssl_grade = analysis_data.get('security_grade', 'F')
        issues = analysis_data.get('issues', [])
        
        business_impact = {
            'revenue_loss_annual': analysis_data.get('annual_loss', 0),
            'seo_impact': analysis_data.get('seo_impact', 0),
            'trust_damage': analysis_data.get('trust_damage', 0)
        }
        
        # 제목
        story.append(Paragraph(f"{domain} 웹사이트 보안 분석 전문 보고서", title_style))
        story.append(Paragraph(f"분석일시: {analysis_data.get('analysis_date', 'N/A')} | SecureCheck Pro", normal_text))
        story.append(Spacer(1, 30))
        
        # === 1. EXECUTIVE SUMMARY (경영진용) ===
        story.append(Paragraph("1. EXECUTIVE SUMMARY", section_heading))
        story.append(Paragraph("경영진 핵심 요약", subsection_heading))
        
        # 핵심 발견사항
        critical_issues = [i for i in issues if i.get('severity') == 'critical']
        high_issues = [i for i in issues if i.get('severity') == 'high']
        
        # 보안 상태 판정
        if security_score >= 80:
            status_color = '#27ae60'
            status_text = '양호'
            risk_level = '낮음'
        elif security_score >= 60:
            status_color = '#f39c12'
            status_text = '주의'
            risk_level = '중간'
        else:
            status_color = '#e74c3c'
            status_text = '위험'
            risk_level = '높음'
            
        executive_summary = f"""
<b>🎯 핵심 발견사항</b><br/>
• 전체 보안 등급: <font color='{status_color}'><b>{ssl_grade}등급 ({status_text})</b></font><br/>
• 보안 점수: {security_score}/100점 (위험도: {risk_level})<br/>
• 치명적 보안 문제: {len(critical_issues)}건<br/>
• 높은 위험 문제: {len(high_issues)}건<br/><br/>

<b>💰 예상 비즈니스 영향</b><br/>
• 연간 예상 손실: <font color='#e74c3c'><b>{business_impact['revenue_loss_annual']:,}원</b></font><br/>
• SEO 순위 하락: 최대 {business_impact['seo_impact']}%<br/>
• 고객 신뢰도 손실: {business_impact['trust_damage']}%<br/><br/>

<b>⚡ 즉시 조치 필요사항</b><br/>
"""
        
        # 즉시 조치사항 추가
        urgent_actions = []
        if len(critical_issues) > 0:
            urgent_actions.append("• 치명적 보안 취약점 즉시 해결 (24시간 내)")
        if ssl_grade in ['F', 'D']:
            urgent_actions.append("• SSL 인증서 설치/교체 (48시간 내)")
        if business_impact['revenue_loss_annual'] > 500000000:
            urgent_actions.append("• 보안 강화로 매출 손실 방지 (1주일 내)")
        if not urgent_actions:
            urgent_actions.append("• 현재 상태 양호, 정기 모니터링 지속")
            
        executive_summary += "<br/>".join(urgent_actions)
        
        story.append(Paragraph(executive_summary, normal_text))
        story.append(Spacer(1, 25))
        
        # === 2. 기술 분석 (개발자용) ===
        story.append(Paragraph("2. 기술 분석 (Technical Analysis)", section_heading))
        story.append(Paragraph("개발팀 상세 기술 정보", subsection_heading))
        
        # SSL/TLS 인증서 상세 분석
        story.append(Paragraph("🔐 SSL/TLS 인증서 분석", subsection_heading))
        
        cert_status = "✅ 유효" if analysis_data.get('certificate_valid', False) else "❌ 유효하지 않음"
        expiry_days = analysis_data.get('days_until_expiry', 0)
        expiry_status = "⚠️ 만료 임박" if expiry_days < 30 else f"✅ {expiry_days}일 남음"
        
        cert_info = f"""
<b>인증서 검증 결과</b><br/>
• 상태: {cert_status}<br/>
• 만료: {expiry_status}<br/>
• 발급기관: {ssl_result.get('issuer_cn', 'N/A')}<br/>
• 주체: {ssl_result.get('subject_cn', 'N/A')}<br/>
• 자체서명: {'예' if ssl_result.get('is_self_signed', False) else '아니오'}<br/>
• SSL 등급: <b>{ssl_grade}</b><br/><br/>
"""
        
        # 구체적 설정 예시 추가
        if ssl_grade in ['F', 'D', 'C']:
            cert_info += """
<b>🔧 SSL 설정 개선 예시 (Apache)</b><br/>
"""
            story.append(Paragraph(cert_info, normal_text))
            
            apache_config = """SSLEngine on
SSLProtocol -all +TLSv1.2 +TLSv1.3
SSLCipherSuite ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS
SSLHonorCipherOrder off"""
            story.append(Paragraph(apache_config, code_style))
        else:
            story.append(Paragraph(cert_info, normal_text))
        
        # 보안 헤더 상세 분석
        story.append(Paragraph("🛡️ 보안 헤더 분석", subsection_heading))
        
        present_headers = analysis_data.get('security_headers_present', [])
        missing_headers = analysis_data.get('missing_security_headers', [])
        
        header_info = ""
        if present_headers:
            header_info += "<b>✅ 설정된 보안 헤더:</b><br/>"
            for header in present_headers:
                header_info += f"• {header}<br/>"
            header_info += "<br/>"
        
        if missing_headers:
            header_info += "<b>❌ 누락된 보안 헤더:</b><br/>"
            for header in missing_headers:
                header_info += f"• {header}<br/>"
            header_info += "<br/>"
            
            # 구체적 헤더 설정 예시
            header_info += """
<b>🔧 누락 헤더 설정 예시</b><br/>
"""
            story.append(Paragraph(header_info, normal_text))
            
            nginx_config = """# nginx 설정 예시
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Content-Security-Policy "default-src 'self'" always;"""
            story.append(Paragraph(nginx_config, code_style))
        else:
            story.append(Paragraph(header_info or "✅ 모든 필수 보안 헤더가 완벽하게 설정되어 있습니다.", normal_text))
        
        story.append(Spacer(1, 20))
        
        # 취약점별 위험도 평가
        story.append(Paragraph("🚨 발견된 취약점 및 위험도 평가", subsection_heading))
        
        if issues:
            # 심각도별 분류
            severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
            for issue in issues:
                severity = issue.get('severity', 'low')
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            severity_summary = f"""
<b>취약점 심각도 분포</b><br/>
🔴 Critical: {severity_counts['critical']}건 | 🟠 High: {severity_counts['high']}건 | 🟡 Medium: {severity_counts['medium']}건 | 🟢 Low: {severity_counts['low']}건<br/><br/>
"""
            story.append(Paragraph(severity_summary, normal_text))
            
            # 각 취약점 상세
            for i, issue in enumerate(issues, 1):
                severity_emoji = {
                    'critical': '🔴',
                    'high': '🟠',
                    'medium': '🟡', 
                    'low': '🟢'
                }.get(issue.get('severity', 'low'), '🔘')
                
                # CVSS 스코어 추정
                cvss_score = {
                    'critical': '9.0-10.0',
                    'high': '7.0-8.9',
                    'medium': '4.0-6.9',
                    'low': '0.1-3.9'
                }.get(issue.get('severity', 'low'), 'N/A')
                
                issue_text = f"""
<b>{i}. {severity_emoji} {issue.get('title', 'Unknown Issue')}</b> [위험도: {issue.get('severity', 'unknown').upper()}] [CVSS: {cvss_score}]<br/>
{issue.get('description', 'No description available.')}<br/><br/>
"""
                story.append(Paragraph(issue_text, normal_text))
        else:
            story.append(Paragraph("✅ 심각한 보안 취약점이 발견되지 않았습니다.", normal_text))
        
        story.append(Spacer(1, 25))
        
        # === 3. 비즈니스 영향 (마케팅/운영팀용) ===
        story.append(Paragraph("3. 비즈니스 영향 분석 (Business Impact)", section_heading))
        story.append(Paragraph("경영진 및 마케팅팀 핵심 지표", subsection_heading))
        
        # ROI 계산 및 매출 영향
        annual_loss = business_impact['revenue_loss_annual']
        monthly_loss = annual_loss // 12 if annual_loss > 0 else 0
        daily_loss = annual_loss // 365 if annual_loss > 0 else 0
        
        business_analysis = f"""
<b>💰 매출 손실 분석</b><br/>
• 연간 예상 손실: <font color='#e74c3c'><b>{annual_loss:,}원</b></font><br/>
• 월간 손실: {monthly_loss:,}원<br/>
• 일일 손실: {daily_loss:,}원<br/><br/>

<b>📈 마케팅 영향</b><br/>
• SEO 순위 하락: {business_impact['seo_impact']}% (Google 검색결과 하위권 이동)<br/>
• 브랜드 신뢰도: {business_impact['trust_damage']}% 손실<br/>
• 고객 이탈률 증가: 예상 {business_impact['trust_damage']//2 if business_impact['trust_damage'] > 0 else 0}%<br/><br/>

<b>🏢 브랜드 리스크 평가</b><br/>
"""
        
        # 브랜드 리스크 레벨 계산
        if security_score < 30:
            risk_level = "극히 위험"
            risk_color = "#c0392b"
            risk_desc = "즉시 대응 필요. 언론 노출시 브랜드 이미지 심각 손상"
        elif security_score < 50:
            risk_level = "높음"
            risk_color = "#e74c3c"
            risk_desc = "신속한 대응 필요. 고객 이탈 가능성 높음"
        elif security_score < 70:
            risk_level = "보통"
            risk_color = "#f39c12"
            risk_desc = "개선 권장. 경쟁사 대비 불리할 수 있음"
        else:
            risk_level = "낮음"
            risk_color = "#27ae60"
            risk_desc = "현재 상태 양호. 지속적 모니터링 권장"
            
        business_analysis += f"• 브랜드 리스크: <font color='{risk_color}'><b>{risk_level}</b></font><br/>"
        business_analysis += f"• 평가: {risk_desc}<br/><br/>"
        
        # ROI 개선 효과
        if annual_loss > 0:
            ssl_cost = 300000  # SSL 인증서 연간 비용 추정
            roi_ratio = annual_loss // ssl_cost if ssl_cost > 0 else 0
            business_analysis += f"""
<b>🎯 보안 개선 ROI</b><br/>
• SSL 보안 강화 투자: 연 약 {ssl_cost:,}원<br/>
• 예상 손실 방지: 연 {annual_loss:,}원<br/>
• <font color='#27ae60'><b>ROI: {roi_ratio}배 투자대비 효과</b></font><br/>
"""
            
        story.append(Paragraph(business_analysis, normal_text))
        story.append(Spacer(1, 25))
        
        # === 4. 실행 계획 (Action Plan) ===
        story.append(Paragraph("4. 실행 계획 (Implementation Roadmap)", section_heading))
        story.append(Paragraph("단계별 해결 방안 및 타임라인", subsection_heading))
        
        # 단계별 실행 계획
        recommendations = analysis_data.get('recommendations', [])
        
        action_plan = f"""
<b>⚡ 즉시 실행 (24-48시간 내)</b><br/>
"""
        
        # 긴급 조치사항
        urgent_count = 0
        if len(critical_issues) > 0:
            action_plan += f"• 치명적 취약점 {len(critical_issues)}건 즉시 수정<br/>"
            urgent_count += 1
        if ssl_grade in ['F']:
            action_plan += "• SSL 인증서 즉시 설치 (Let's Encrypt 권장)<br/>"
            urgent_count += 1
        if not urgent_count:
            action_plan += "• 현재 긴급 조치사항 없음<br/>"
            
        action_plan += "<br/><b>📅 단기 실행 (1주일 내)</b><br/>"
        
        # 단기 조치사항
        shortterm_count = 0
        if len(high_issues) > 0:
            action_plan += f"• 높은 위험도 문제 {len(high_issues)}건 해결<br/>"
            shortterm_count += 1
        if ssl_grade in ['D', 'C']:
            action_plan += "• SSL 설정 강화 (TLS 1.3, 강력한 암호화)<br/>"
            shortterm_count += 1
        if len(missing_headers) > 0:
            action_plan += f"• 보안 헤더 {len(missing_headers)}개 추가 설정<br/>"
            shortterm_count += 1
        if not shortterm_count:
            action_plan += "• HTTP → HTTPS 리다이렉션 점검<br/>"
            
        action_plan += "<br/><b>🗓️ 장기 실행 (1개월 내)</b><br/>"
        action_plan += "• 보안 모니터링 시스템 구축<br/>"
        action_plan += "• 정기 보안 점검 일정 수립<br/>"
        action_plan += "• 직원 보안 교육 실시<br/><br/>"
        
        # 예상 비용 및 시간
        ssl_setup_cost = 0 if 'Let\'s Encrypt' in str(recommendations) else 200000
        consulting_cost = len(critical_issues) * 500000 + len(high_issues) * 200000
        total_cost = ssl_setup_cost + consulting_cost + 300000  # 기본 설정 비용
        
        action_plan += f"""
<b>💰 예상 투자 비용</b><br/>
• SSL 인증서: {ssl_setup_cost:,}원 (무료 SSL 사용시 0원)<br/>
• 보안 컨설팅: {consulting_cost:,}원<br/>
• 설정 및 구축: 300,000원<br/>
• <b>총 예상 비용: {total_cost:,}원</b><br/><br/>

<b>⏱️ 예상 소요 시간</b><br/>
• 긴급 조치: 1-2일<br/>
• 전체 완료: 1-2주<br/>
• 투자회수기간: 즉시 (손실 방지 효과)<br/><br/>

<b>📊 성공 측정 기준</b><br/>
• SSL 등급 A 이상 달성<br/>
• 보안 점수 85점 이상<br/>
• 취약점 0건 달성<br/>
• 고객 이탈률 정상화
"""
        
        story.append(Paragraph(action_plan, normal_text))
        story.append(Spacer(1, 25))
        
        # 결론
        story.append(Paragraph("5. 결론 및 권고사항", section_heading))
        roi_ratio = annual_loss // 300000 if annual_loss > 0 and annual_loss >= 300000 else 1
        final_conclusion = f"""
<b>🎯 종합 평가</b><br/>
현재 웹사이트의 보안 등급은 <font color='{status_color}'><b>{ssl_grade}</b></font>이며, 전체 보안 점수는 <b>{security_score}/100점</b>입니다.
연간 <font color='#e74c3c'><b>{annual_loss:,}원</b></font>의 손실이 예상되므로 즉시 보안 강화 조치가 필요합니다.<br/><br/>

<b>✅ 최우선 권고사항</b><br/>
1. SSL 보안 강화를 통한 즉각적인 손실 방지<br/>
2. 보안 모니터링 체계 구축으로 지속적 관리<br/>
3. 정기적인 보안 점검을 통한 예방적 관리<br/><br/>

투자 대비 효과가 매우 높으므로(<b>{roi_ratio}배</b>), 신속한 실행을 강력히 권장합니다.
"""
        story.append(Paragraph(final_conclusion, normal_text))
        story.append(Spacer(1, 20))
        
        # 푸터
        footer_text = """
---
<b>SecureCheck Pro</b> - 웹사이트 보안 전문 분석 서비스<br/>
본 보고서는 PRD 명세에 따라 전문적으로 생성되었습니다.
"""
        story.append(Paragraph(footer_text, normal_text))

        # PDF 생성
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        # 오류 발생시 간단한 보고서라도 생성
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        error_story = [
            Paragraph("보안 분석 보고서 생성 오류", styles['Title']),
            Spacer(1, 20),
            Paragraph(f"도메인: {analysis_data.get('domain', 'Unknown')}", styles['Normal']),
            Paragraph(f"오류 내용: {str(e)}", styles['Normal']),
            Spacer(1, 10),
            Paragraph("기본 정보:", styles['Heading2']),
            Paragraph(f"SSL 등급: {analysis_data.get('security_grade', 'F')}", styles['Normal']),
            Paragraph(f"보안 점수: {analysis_data.get('security_score', 0)}/100", styles['Normal'])
        ]
        
        doc.build(error_story)
        buffer.seek(0)
        return buffer.getvalue()

def create_basic_pdf() -> bytes:
    """기본적인 PDF를 생성합니다."""
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    # 아주 기본적인 텍스트
    c.drawString(100, 750, "Security Analysis Report")
    c.drawString(100, 700, "Basic PDF Generation Test")

    c.save()
    buffer.seek(0)
    return buffer.getvalue()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)