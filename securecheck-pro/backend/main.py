from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
import uuid
import asyncio
from datetime import datetime
import os

from ssl_analyzer import SSLAnalyzer
try:
    from report_generator_tsc import create_tsc_style_pdf_report
    PDF_GENERATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: PDF generation not available: {e}")
    PDF_GENERATION_AVAILABLE = False
    def create_tsc_style_pdf_report(data):
        return b"PDF generation not available - WeasyPrint dependencies missing"
from ssl_analysis_service import SSLAnalysisService
from business_impact_service import BusinessImpactService
from error_handling import ErrorHandler, URLValidator, ValidationError
from config import API_CONFIG

# 분석 결과를 저장할 메모리 저장소 (실제로는 데이터베이스를 사용해야 함)
analysis_results = {}

# Initialize services
ssl_analysis_service = SSLAnalysisService()
business_impact_service = BusinessImpactService()

app = FastAPI(
    title="원클릭 SSL체크 API",
    description="웹사이트 SSL/TLS 보안을 원클릭으로 분석하고 보고서를 생성하는 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=API_CONFIG["cors_origins"],
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

@app.get("/")
async def root():
    """Serve the main HTML file"""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "원클릭 SSL체크 API", "version": "1.0.0"}

@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_website(request: AnalyzeRequest):
    """웹사이트 보안 분석을 수행합니다."""
    url = str(request.url)
    analysis_id = str(uuid.uuid4())
    
    try:
        # URL 검증
        URLValidator.validate_url(url)
        
        # 실제 SSL 분석 수행
        ssl_result = await ssl_analyzer.analyze(url)
        
        # 보안 점수 계산
        security_score = ssl_analysis_service.calculate_security_score(ssl_result)
        
        # 문제점 추출
        issues = ssl_analysis_service.extract_security_issues(ssl_result)
        
        # 비즈니스 영향 계산
        business_impact = business_impact_service.calculate_business_impact(
            security_score, ssl_result, issues
        )
        
        # 개선 권장사항 생성
        recommendations = business_impact_service.generate_business_recommendations(
            ssl_result, issues
        )
        
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
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise ErrorHandler.handle_analysis_error(e, analysis_id, url)

@app.get("/api/v1/reports/{report_id}/html")
async def get_report_html(report_id: str):
    """분석 결과의 HTML 보고서를 반환합니다."""
    from fastapi.responses import HTMLResponse
    from report_generator_tsc import _generate_tsc_html_report, _get_tsc_html_template
    
    try:
        # 저장된 분석 결과 조회
        if report_id not in analysis_results:
            raise HTTPException(status_code=404, detail=f"분석 결과가 존재하지 않습니다: {report_id}")

        saved_result = analysis_results[report_id]
        ssl_result = saved_result.get("ssl_result", {})

        # HTML용 데이터 구성 (템플릿과 키 이름 일치)
        analysis_data = {
            "domain": ssl_result.get("domain", saved_result.get("url", "").replace("https://", "").replace("http://", "")),
            "analysis_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "ssl_grade": ssl_result.get("ssl_grade", "F"),
            "security_score": saved_result.get("security_score", 0),
            "certificate_valid": ssl_result.get("certificate_valid", False),
            "days_until_expiry": ssl_result.get("days_until_expiry", 0),
            "missing_headers": ssl_result.get("missing_security_headers", []),
            "annual_revenue_loss": 50000000,  # 기본값
            "server_info": {"software": "nginx"},  # 기본값
            "redirects_https": ssl_result.get("ssl_grade", "F") != "F",
            "response_headers": {}
        }

        # HTML 생성
        html_content = _generate_tsc_html_report(analysis_data)
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        print(f"HTML 생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"HTML 생성 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/v1/reports/{report_id}/download")
async def download_report(report_id: str):
    """HTML 보고서로 리다이렉트 - 사용자가 브라우저 인쇄 기능으로 PDF 다운로드 가능"""
    from fastapi.responses import RedirectResponse
    print(f"HTML 보고서 리다이렉트: {report_id}")
    
    # HTML 보고서로 리다이렉트
    return RedirectResponse(url=f"/api/v1/reports/{report_id}/html")

@app.post("/api/v1/reports/generate-pdf")
async def generate_pdf_report(request: dict):
    """HTML 보고서 생성 (옵션널 - 서버사이드 PDF 생성용)."""
    try:
        analysis_data = request.get("analysis_data", {})
        from report_generator_tsc import _generate_tsc_html_report
        html_content = _generate_tsc_html_report(analysis_data)

        return {
            "success": True,
            "html_size": len(html_content),
            "message": "HTML 보고서 생성 완료 - 브라우저 인쇄 기능을 사용하세요"
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

# PDF generation is handled by report_generator_tsc.py

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)