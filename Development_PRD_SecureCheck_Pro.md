# SecureCheck Pro - 개발 PRD (Product Requirements Document)

**프로젝트명**: SecureCheck Pro (웹사이트 보안 자동 분석기)  
**개발 접근법**: Fixed Flow 기반 (No AI/LLM)  
**작성일**: 2025년 9월 2일  
**버전**: 1.0  

---

## 📋 개발 개요

### 핵심 설계 원칙
- **AI/LLM 완전 배제**: 고정된 플로우와 템플릿 기반 보고서 생성
- **결정론적 분석**: 동일 입력 → 동일 출력 보장
- **케이스 기반 분석**: 모든 SSL 상태를 사전 정의된 케이스로 분류
- **템플릿 기반 보고서**: 각 케이스별 고정 템플릿 사용

### 기술 아키텍처 (Playwright 기반)
```
Frontend (React/Next.js)
    ↓ URL 입력
Analysis Engine (Python/FastAPI + Playwright) 
    ├── Browser Automation (Playwright)
    │   ├── SSL Status Scanner (브라우저 기반)
    │   ├── Security Warning Detector (실제 경고 캡처)
    │   └── Performance Measurement (실제 로딩)
    ├── Network Analysis (Python)
    │   ├── Certificate Inspector (OpenSSL)
    │   ├── Headers Analyzer (HTTP 요청)
    │   └── Port Scanner (Socket)
    └── Business Impact Calculator (고정 공식)
    ↓ 시나리오별 분류 결과
Report Generator (Template Engine)
    ├── Scenario-based Template Selector
    ├── Data Injection (Jinja2)
    └── PDF Generator (WeasyPrint)
    ↓
Database (PostgreSQL) + Screenshots (Local/S3)
```

---

## 🔍 SSL 상태별 케이스 정의 및 분석 로직

### 케이스 1: SSL 완전 부재
**탐지 로직**:
```python
def detect_no_ssl(domain: str) -> dict:
    try:
        # 443 포트 연결 테스트
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((domain, 443))
        sock.close()
        
        return {
            'has_ssl': result == 0,
            'port_443_open': result == 0,
            'connection_error': 'Connection refused' if result != 0 else None,
            'ssl_case_type': 'no_ssl' if result != 0 else 'has_ssl'
        }
    except Exception as e:
        return {
            'has_ssl': False,
            'connection_error': str(e),
            'ssl_case_type': 'no_ssl'
        }
```

**상세 체크 항목**:
- 포트 443 연결 상태 (open/closed/filtered)
- HTTP 서비스 가용성 (포트 80)
- DNS 해석 가능 여부
- 서버 응답 시간 측정

**위험도 계산**:
```python
risk_score = 100  # 최고 위험도
business_impact = {
    'user_loss_rate': 0.8,  # 80% 이탈
    'seo_penalty': 0.4,     # 40% 순위 하락
    'trust_damage': 0.9     # 90% 신뢰도 손상
}
```

**보고서 템플릿**: `no_ssl_template.html`

### 케이스 2: 자체 서명 인증서 + 서버 오류
**탐지 로직**:
```python
def detect_self_signed(domain: str) -> dict:
    cert_info = get_ssl_certificate(domain)
    subject = cert_info['subject']
    issuer = cert_info['issuer']
    
    # 서버 응답 테스트
    server_response = test_https_response(domain)
    
    return {
        'is_self_signed': subject == issuer,
        'subject': subject,
        'issuer': issuer,
        'valid_from': cert_info['notBefore'],
        'valid_to': cert_info['notAfter'],
        'server_issues': server_response,
        'has_additional_errors': server_response.get('status_code', 200) != 200
    }
```

**서버 오류 세부 분석**:
```python
def test_https_response(domain: str) -> dict:
    try:
        response = requests.get(f'https://{domain}', timeout=10, verify=False)
        return {
            'status_code': response.status_code,
            'response_time': response.elapsed.total_seconds() * 1000,  # ms
            'server_header': response.headers.get('Server', 'Unknown'),
            'content_length': len(response.content),
            'has_406_error': response.status_code == 406,
            'has_500_error': response.status_code >= 500,
            'redirect_count': len(response.history)
        }
    except requests.exceptions.SSLError as e:
        return {'ssl_error': str(e)}
    except requests.exceptions.ConnectionError as e:
        return {'connection_error': str(e)}
    except Exception as e:
        return {'unknown_error': str(e)}
```

**특별 케이스: 406 Not Acceptable 에러**:
- **원인 분석**: nginx Accept 헤더 처리 오류, PHP 애플리케이션 HTTPS 처리 실패
- **추가 체크**: 프록시 설정, SSL Termination 설정
- **해결 우선순위**: SSL 교체 전에 서버 설정 수정 필요

**보고서 템플릿**: `self_signed_template.html`

### 케이스 3: 만료된 인증서
**탐지 로직**:
```python
def detect_expired_cert(domain: str) -> dict:
    cert_info = get_ssl_certificate(domain)
    expiry_date = datetime.strptime(cert_info['notAfter'], '%b %d %H:%M:%S %Y %Z')
    now = datetime.utcnow()
    
    days_until_expiry = (expiry_date - now).days
    
    return {
        'is_expired': days_until_expiry < 0,
        'expires_soon': 0 <= days_until_expiry <= 30,
        'days_until_expiry': days_until_expiry,
        'expiry_date': expiry_date.isoformat()
    }
```

**보고서 템플릿**: `expired_cert_template.html`

### 케이스 4: 도메인 불일치
**탐지 로직**:
```python
def detect_domain_mismatch(domain: str) -> dict:
    cert_info = get_ssl_certificate(domain)
    cert_domains = extract_domains_from_cert(cert_info)
    
    return {
        'is_match': domain in cert_domains,
        'cert_domains': cert_domains,
        'wildcard_match': any(d.startswith('*.') and domain.endswith(d[2:]) for d in cert_domains)
    }
```

**보고서 템플릿**: `domain_mismatch_template.html`

### 케이스 5: 정상 SSL
**탐지 로직**:
```python
def detect_valid_ssl(domain: str) -> dict:
    cert_info = get_ssl_certificate(domain)
    ssl_labs_grade = get_ssl_labs_grade(domain)  # API 호출
    
    return {
        'is_valid': True,
        'ssl_grade': ssl_labs_grade,
        'issuer': cert_info['issuer'],
        'encryption_strength': analyze_cipher_strength(domain),
        'protocol_support': check_tls_protocols(domain)
    }
```

**보고서 템플릿**: `valid_ssl_template.html`

### 🆕 템플릿 작업에서 발견한 추가 케이스들

#### 브라우저별 경고 메시지 케이스
```python
def get_browser_warnings(ssl_case_type: str) -> List[dict]:
    """브라우저별 경고 메시지 매핑"""
    browser_data = {
        'no_ssl': {
            'Chrome': {'icon': '🟡', 'message': '안전하지 않음 - 이 사이트로 전송하는 정보가 안전하지 않습니다'},
            'Firefox': {'icon': '🔓', 'message': '안전하지 않은 연결 - 자물쇠 해제 아이콘'},
            'Safari': {'icon': '⚠️', 'message': '안전하지 않습니다 - 개인정보 입력시 추가 경고'},
            'Edge': {'icon': '⚠️', 'message': '안전하지 않음 - SmartScreen 보호 기능 작동'}
        },
        'self_signed': {
            'Chrome': {'icon': '⚠️', 'message': '이 연결은 비공개 연결이 아닙니다'},
            'Firefox': {'icon': '⚠️', 'message': '보안 연결 실패'},
            'Safari': {'icon': '⚠️', 'message': '이 연결은 안전하지 않습니다'},
            'Edge': {'icon': '⚠️', 'message': '이 사이트는 안전하지 않습니다'}
        },
        'expired': {
            'Chrome': {'icon': '❌', 'message': 'NET::ERR_CERT_DATE_INVALID - 서버의 인증서가 만료되었습니다'},
            'Firefox': {'icon': '❌', 'message': 'SEC_ERROR_EXPIRED_CERTIFICATE'},
            'Safari': {'icon': '❌', 'message': '인증서가 유효하지 않습니다'},
            'Edge': {'icon': '❌', 'message': '인증서 오류: 인증서가 만료되었습니다'}
        }
    }
    return browser_data.get(ssl_case_type, {})
```

#### 보안 헤더 분석 케이스
```python
SECURITY_HEADERS = {
    'Strict-Transport-Security': {
        'weight': 4,  # 가중치
        'critical': True,
        'description': 'HTTPS 강제 연결',
        'recommendation': 'max-age=31536000; includeSubDomains; preload'
    },
    'X-Frame-Options': {
        'weight': 3,
        'critical': True,
        'description': 'Clickjacking 방지',
        'recommendation': 'DENY 또는 SAMEORIGIN'
    },
    'X-Content-Type-Options': {
        'weight': 2,
        'critical': False,
        'description': 'MIME 타입 스니핑 방지',
        'recommendation': 'nosniff'
    },
    'Content-Security-Policy': {
        'weight': 4,
        'critical': True,
        'description': 'XSS 및 데이터 삽입 공격 방지',
        'recommendation': "default-src 'self'"
    },
    'X-XSS-Protection': {
        'weight': 2,
        'critical': False,
        'description': 'XSS 필터링 활성화',
        'recommendation': '1; mode=block'
    },
    'Referrer-Policy': {
        'weight': 1,
        'critical': False,
        'description': '리퍼러 정보 제어',
        'recommendation': 'strict-origin-when-cross-origin'
    }
}

def analyze_security_headers(headers: dict) -> dict:
    total_score = 0
    max_score = sum(h['weight'] for h in SECURITY_HEADERS.values())
    
    for header_name, header_config in SECURITY_HEADERS.items():
        if header_name in headers:
            # 헤더 값 품질 평가
            header_value = headers[header_name]
            quality_score = evaluate_header_quality(header_name, header_value)
            total_score += header_config['weight'] * quality_score
    
    return {
        'total_score': total_score,
        'max_score': max_score,
        'percentage': (total_score / max_score) * 100,
        'missing_critical': [h for h, config in SECURITY_HEADERS.items() 
                           if config['critical'] and h not in headers]
    }
```

#### 성능 측정 케이스
```python
def measure_performance_impact(domain: str) -> dict:
    """SSL 적용이 성능에 미치는 영향 측정"""
    performance_data = {}
    
    # HTTP vs HTTPS 응답시간 비교
    http_time = measure_response_time(f'http://{domain}')
    https_time = measure_response_time(f'https://{domain}')
    
    ssl_overhead = https_time - http_time if https_time and http_time else 0
    
    return {
        'http_response_time': http_time,
        'https_response_time': https_time,
        'ssl_overhead': ssl_overhead,
        'ssl_overhead_percentage': (ssl_overhead / http_time * 100) if http_time else 0,
        'http2_support': check_http2_support(domain),
        'compression_enabled': check_compression(domain),
        'performance_grade': calculate_performance_grade(https_time, ssl_overhead)
    }
```

#### 암호화 품질 분석 케이스
```python
def analyze_cipher_quality(domain: str) -> dict:
    """암호화 스위트 및 프로토콜 품질 분석"""
    try:
        # TLS 버전 지원 확인
        supported_tls = []
        for version in ['TLSv1.3', 'TLSv1.2', 'TLSv1.1', 'TLSv1.0']:
            if check_tls_version(domain, version):
                supported_tls.append(version)
        
        # Cipher Suite 분석
        cipher_info = get_cipher_suites(domain)
        
        return {
            'supported_tls_versions': supported_tls,
            'highest_tls_version': supported_tls[0] if supported_tls else None,
            'cipher_suites': cipher_info['suites'],
            'forward_secrecy': cipher_info['has_forward_secrecy'],
            'encryption_strength': cipher_info['max_key_size'],
            'weak_ciphers': cipher_info['weak_ciphers'],
            'deprecated_protocols': [v for v in supported_tls if v in ['TLSv1.0', 'TLSv1.1']]
        }
    except Exception as e:
        return {'analysis_error': str(e)}
```

#### 보안 점수 계산 시스템 (고정 공식)
```python
class SecurityScoreCalculator:
    """고정 공식 기반 보안 점수 계산기"""
    
    WEIGHTS = {
        'ssl_certificate': 40,    # SSL 인증서 (40점)
        'security_headers': 20,   # 보안 헤더 (20점)
        'tls_protocols': 15,      # 프로토콜 지원 (15점)
        'cipher_strength': 25     # 암호화 강도 (25점)
    }
    
    def calculate_total_score(self, ssl_result: dict, headers_result: dict, 
                            protocols_result: dict, cipher_result: dict) -> int:
        """총 보안 점수 계산"""
        ssl_score = self._calculate_ssl_score(ssl_result)
        headers_score = self._calculate_headers_score(headers_result)
        protocol_score = self._calculate_protocol_score(protocols_result)
        cipher_score = self._calculate_cipher_score(cipher_result)
        
        total = ssl_score + headers_score + protocol_score + cipher_score
        return min(100, total)
    
    def _calculate_ssl_score(self, ssl_result: dict) -> int:
        """SSL 인증서 점수 (40점 만점)"""
        if ssl_result.get('ssl_case_type') == 'no_ssl':
            return 0
        elif ssl_result.get('ssl_case_type') == 'expired':
            return 5  # 만료된 인증서
        elif ssl_result.get('ssl_case_type') == 'self_signed':
            base_score = 10
            # 서버 오류가 있으면 추가 감점
            if ssl_result.get('has_additional_errors'):
                base_score -= 5
            return max(0, base_score)
        elif ssl_result.get('ssl_case_type') == 'domain_mismatch':
            return 15
        elif ssl_result.get('ssl_case_type') == 'valid':
            # SSL Labs 등급별 점수
            grade_mapping = {
                'A+': 40, 'A': 35, 'B': 30, 'C': 25, 'D': 15, 'F': 5
            }
            return grade_mapping.get(ssl_result.get('ssl_labs_grade', 'F'), 5)
        
        return 0
    
    def _calculate_headers_score(self, headers_result: dict) -> int:
        """보안 헤더 점수 (20점 만점)"""
        if not headers_result:
            return 0
            
        weighted_score = 0
        max_weighted_score = sum(SECURITY_HEADERS[h]['weight'] for h in SECURITY_HEADERS)
        
        for header_name, header_config in SECURITY_HEADERS.items():
            if headers_result.get(header_name, {}).get('present'):
                quality = evaluate_header_quality(header_name, headers_result[header_name]['value'])
                weighted_score += header_config['weight'] * quality
        
        return int((weighted_score / max_weighted_score) * 20)

def score_to_grade(score: int) -> tuple[str, str]:
    """점수를 등급으로 변환"""
    if score >= 95:
        return ('A+', 'aplus')
    elif score >= 85:
        return ('A', 'a')
    elif score >= 75:
        return ('B', 'b')
    elif score >= 65:
        return ('C', 'c')
    elif score >= 50:
        return ('D', 'd')
    else:
        return ('F', 'f')
```

#### 비즈니스 영향 계산 케이스 (업종별)
```python
BUSINESS_IMPACT_MODELS = {
    'manufacturing': {  # 제조업 (B2B 중심)
        'base_conversion_rate': 0.015,  # 1.5% 문의 전환
        'order_conversion_rate': 0.08,  # 8% 수주 전환
        'average_order_value': 20000000,  # 평균 수주 2천만원
        'ssl_trust_factor': 0.9,  # SSL 문제시 신뢰도 90% 하락
        'b2b_security_importance': 0.95  # B2B에서 보안 중요도 95%
    },
    'ecommerce': {  # 이커머스 (B2C 중심)
        'base_conversion_rate': 0.025,  # 2.5% 구매 전환
        'average_order_value': 150000,  # 평균 주문 15만원
        'ssl_trust_factor': 0.85,  # SSL 문제시 85% 이탈
        'mobile_traffic_ratio': 0.7,  # 모바일 트래픽 70%
        'payment_security_importance': 0.99  # 결제 보안 중요도 99%
    },
    'service': {  # 서비스업 (리드 제너레이션)
        'base_conversion_rate': 0.035,  # 3.5% 문의 전환
        'lead_value': 500000,  # 리드당 가치 50만원
        'ssl_trust_factor': 0.7,  # SSL 문제시 70% 이탈
        'content_trust_importance': 0.8  # 콘텐츠 신뢰 중요도 80%
    }
}

def calculate_business_impact_by_industry(domain: str, ssl_case_type: str, 
                                       industry: str = 'manufacturing') -> dict:
    """업종별 비즈니스 영향 계산"""
    model = BUSINESS_IMPACT_MODELS.get(industry, BUSINESS_IMPACT_MODELS['manufacturing'])
    
    # 추정 월 방문자 (도메인 규모에 따라 조정 필요)
    estimated_monthly_visitors = estimate_traffic_by_domain_age(domain)
    
    # SSL 케이스별 이탈률
    loss_rates = {
        'no_ssl': 0.8,      # 80% 이탈
        'self_signed': 0.6,  # 60% 이탈
        'expired': 0.7,      # 70% 이탈
        'domain_mismatch': 0.4,  # 40% 이탈
        'valid': 0.05       # 5% 기본 이탈
    }
    
    user_loss_rate = loss_rates.get(ssl_case_type, 0.5)
    lost_users = estimated_monthly_visitors * user_loss_rate
    
    if industry == 'manufacturing':
        monthly_loss = (lost_users * model['base_conversion_rate'] * 
                       model['order_conversion_rate'] * model['average_order_value'])
    elif industry == 'ecommerce':
        monthly_loss = lost_users * model['base_conversion_rate'] * model['average_order_value']
    else:  # service
        monthly_loss = lost_users * model['base_conversion_rate'] * model['lead_value']
    
    return {
        'monthly_visitors': estimated_monthly_visitors,
        'user_loss_rate': user_loss_rate * 100,
        'lost_users_monthly': lost_users,
        'lost_users_daily': lost_users / 30,
        'monthly_loss': monthly_loss,
        'annual_loss': monthly_loss * 12,
        'industry': industry,
        'trust_factor': model.get('ssl_trust_factor', 0.8) * 100
    }
```

#### 서버 오류 상태별 세부 케이스
```python
HTTP_STATUS_CASES = {
    200: {
        'severity': 'success',
        'message': '정상 응답',
        'action_required': False
    },
    301: {
        'severity': 'info', 
        'message': 'HTTP → HTTPS 리다이렉션 (권장 설정)',
        'action_required': False
    },
    302: {
        'severity': 'warning',
        'message': '임시 리다이렉션 (영구 리다이렉션 권장)',
        'action_required': True,
        'recommendation': '301 Permanent Redirect 사용 권장'
    },
    403: {
        'severity': 'warning',
        'message': '접근 금지 - 방화벽 또는 서버 설정 문제',
        'action_required': True,
        'recommendation': '서버 접근 권한 및 방화벽 설정 확인'
    },
    404: {
        'severity': 'warning', 
        'message': '페이지를 찾을 수 없음',
        'action_required': True,
        'recommendation': 'HTTPS 버전 사이트 설정 확인'
    },
    406: {
        'severity': 'critical',
        'message': 'Accept 헤더 처리 오류 - nginx/Apache 설정 문제',
        'action_required': True,
        'recommendation': '프록시 설정 및 Accept 헤더 처리 로직 수정',
        'technical_details': 'nginx proxy_set_header Accept $http_accept 설정 필요'
    },
    500: {
        'severity': 'critical',
        'message': '내부 서버 오류 - 애플리케이션 레벨 문제',
        'action_required': True,
        'recommendation': '서버 로그 확인 및 애플리케이션 디버깅 필요'
    },
    502: {
        'severity': 'critical',
        'message': 'Bad Gateway - 프록시 서버 연결 문제',
        'action_required': True,
        'recommendation': '백엔드 서버 상태 및 프록시 설정 확인'
    },
    503: {
        'severity': 'critical',
        'message': '서비스 일시 중단',
        'action_required': True,
        'recommendation': '서버 과부하 또는 점검 상태 확인'
    }
}
```

#### 고객 세그먼트별 행동 패턴 케이스
```python
CUSTOMER_BEHAVIOR_MODELS = {
    'security_conscious': {  # 보안 의식이 높은 고객
        'percentage': 25,    # 전체 방문자의 25%
        'ssl_sensitivity': 0.95,  # SSL 문제에 95% 민감
        'churn_rate_no_ssl': 0.9,  # SSL 없으면 90% 이탈
        'churn_rate_self_signed': 0.8,  # 자체서명이면 80% 이탈
        'behavior_steps': [
            {'description': '웹사이트 접속', 'outcome': '보안 상태 즉시 확인', 'outcome_class': 'neutral'},
            {'description': '보안 경고 발견', 'outcome': '신뢰도 의심', 'outcome_class': 'negative'},
            {'description': '보안 정책 확인', 'outcome': '접속 중단', 'outcome_class': 'critical'},
            {'description': '대안 검색', 'outcome': '경쟁사 이동', 'outcome_class': 'lost'}
        ]
    },
    'general_users': {  # 일반 사용자
        'percentage': 50,
        'ssl_sensitivity': 0.6,
        'churn_rate_no_ssl': 0.5,  # 50% 이탈
        'churn_rate_self_signed': 0.3,  # 30% 이탈
        'behavior_steps': [
            {'description': '웹사이트 접속', 'outcome': '경고 메시지 확인', 'outcome_class': 'warning'},
            {'description': '잠시 망설임', 'outcome': '일부는 계속 진행', 'outcome_class': 'neutral'},
            {'description': '개인정보 입력 단계', 'outcome': '추가 경고로 일부 이탈', 'outcome_class': 'warning'},
            {'description': '서비스 이용', 'outcome': '불안감 속에 이용', 'outcome_class': 'partial'}
        ]
    },
    'b2b_decision_makers': {  # 기업 구매 담당자
        'percentage': 15,
        'ssl_sensitivity': 0.98,  # 매우 높은 민감도
        'churn_rate_no_ssl': 0.95,  # 95% 이탈
        'churn_rate_self_signed': 0.85,  # 85% 이탈
        'behavior_steps': [
            {'description': 'IT팀 보안 검토', 'outcome': '보안 기준 미달 판정', 'outcome_class': 'critical'},
            {'description': '구매팀 보고', 'outcome': '공급업체 제외', 'outcome_class': 'critical'},
            {'description': '대안 업체 검토', 'outcome': '경쟁사 선정', 'outcome_class': 'lost'},
            {'description': '향후 재고려', 'outcome': '장기간 배제', 'outcome_class': 'lost'}
        ]
    },
    'mobile_users': {  # 모바일 사용자
        'percentage': 60,  # 전체 트래픽의 60%
        'ssl_sensitivity': 0.8,
        'churn_rate_no_ssl': 0.7,  # 70% 이탈 (모바일이 더 엄격)
        'churn_rate_self_signed': 0.6,  # 60% 이탈
        'behavior_steps': [
            {'description': '모바일 브라우저 접속', 'outcome': '더 강한 보안 경고', 'outcome_class': 'critical'},
            {'description': '차단 메시지 표시', 'outcome': '접속 자체가 어려움', 'outcome_class': 'critical'},
            {'description': '우회 접속 시도', 'outcome': '복잡한 절차로 포기', 'outcome_class': 'lost'},
            {'description': 'PC로 재접속', 'outcome': '일부만 PC 재시도', 'outcome_class': 'partial'}
        ]
    }
}
```

---

## 🎨 고정 플로우 기반 UI/UX 시나리오

### 메인 분석 플로우
```
1. URL 입력 화면
   ├── 입력 검증 (도메인 형식, 접근 가능성)
   └── 분석 시작 버튼

2. 분석 진행 화면 (Progress Bar)
   ├── Step 1: 기본 연결 테스트 (10초)
   ├── Step 2: SSL 인증서 분석 (15초)
   ├── Step 3: 보안 헤더 검사 (10초)
   ├── Step 4: 성능 측정 (10초)
   └── Step 5: 보고서 생성 (5초)

3. 결과 요약 화면
   ├── 보안 등급 (A+ ~ F)
   ├── 발견된 주요 문제 (최대 5개)
   ├── 비즈니스 영향 요약
   └── 상세 보고서 다운로드 버튼

4. 상세 보고서 페이지
   ├── Executive Summary
   ├── 기술적 분석 결과
   ├── 비즈니스 영향 분석
   └── 구체적 해결 방안
```

### UI 컴포넌트별 설계

#### 1. URL 입력 컴포넌트
```typescript
interface URLInputProps {
  onAnalyze: (url: string) => void;
  isLoading: boolean;
}

const URLInput: React.FC<URLInputProps> = ({ onAnalyze, isLoading }) => {
  const [url, setUrl] = useState('');
  const [validationError, setValidationError] = useState('');

  const validateURL = (input: string): boolean => {
    const urlRegex = /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$/;
    return urlRegex.test(input);
  };

  return (
    <div className="url-input-container">
      <input 
        type="text" 
        placeholder="https://example.com" 
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        className={validationError ? 'error' : ''}
      />
      <button 
        onClick={() => onAnalyze(url)}
        disabled={!validateURL(url) || isLoading}
        className="analyze-btn"
      >
        {isLoading ? '분석 중...' : '보안 분석 시작'}
      </button>
      {validationError && <span className="error-message">{validationError}</span>}
    </div>
  );
};
```

#### 2. 분석 진행 컴포넌트
```typescript
interface AnalysisStep {
  name: string;
  description: string;
  duration: number;
  status: 'pending' | 'running' | 'completed' | 'error';
}

const ProgressTracker: React.FC<{ steps: AnalysisStep[] }> = ({ steps }) => {
  return (
    <div className="progress-container">
      <h3>웹사이트 보안 분석 진행 중...</h3>
      {steps.map((step, index) => (
        <div key={index} className={`step step-${step.status}`}>
          <div className="step-indicator">
            {step.status === 'completed' && '✓'}
            {step.status === 'running' && '⟳'}
            {step.status === 'error' && '✗'}
            {step.status === 'pending' && '○'}
          </div>
          <div className="step-content">
            <h4>{step.name}</h4>
            <p>{step.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
};
```

#### 3. 결과 요약 컴포넌트
```typescript
interface SecurityGrade {
  grade: 'A+' | 'A' | 'B' | 'C' | 'D' | 'F';
  score: number;
  color: 'green' | 'yellow' | 'orange' | 'red';
}

interface AnalysisResult {
  domain: string;
  grade: SecurityGrade;
  issues: SecurityIssue[];
  businessImpact: BusinessImpact;
  analysisDate: string;
}

const ResultSummary: React.FC<{ result: AnalysisResult }> = ({ result }) => {
  return (
    <div className="result-summary">
      <div className="grade-section">
        <div className={`grade-circle grade-${result.grade.color}`}>
          <span className="grade-letter">{result.grade.grade}</span>
          <span className="grade-score">{result.grade.score}/100</span>
        </div>
        <h2>{result.domain} 보안 분석 결과</h2>
      </div>
      
      <div className="issues-section">
        <h3>발견된 주요 문제점</h3>
        {result.issues.map((issue, index) => (
          <div key={index} className={`issue-item severity-${issue.severity}`}>
            <span className="issue-icon">⚠️</span>
            <span className="issue-title">{issue.title}</span>
            <span className="issue-impact">{issue.businessImpact}</span>
          </div>
        ))}
      </div>

      <div className="actions-section">
        <button className="btn btn-primary" onClick={() => downloadReport()}>
          📄 상세 보고서 다운로드 (PDF)
        </button>
        <button className="btn btn-secondary" onClick={() => analyzeAnother()}>
          🔍 다른 웹사이트 분석
        </button>
      </div>
    </div>
  );
};
```

---

## 📊 케이스별 보고서 템플릿 정의

### 보고서 구조 (모든 케이스 공통)
```html
<!-- base_template.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ domain }} 웹사이트 보안 분석 보고서</title>
    <style>{{ css_styles }}</style>
</head>
<body>
    <div class="report-header">
        <h1>웹사이트 보안 분석 보고서</h1>
        <div class="report-meta">
            <p><strong>분석 대상:</strong> {{ domain }}</p>
            <p><strong>분석 일시:</strong> {{ analysis_date }}</p>
            <p><strong>보고서 생성:</strong> {{ report_date }}</p>
            <p><strong>보안 등급:</strong> <span class="grade grade-{{ grade_class }}">{{ security_grade }}</span></p>
        </div>
    </div>

    {% block executive_summary %}{% endblock %}
    {% block technical_analysis %}{% endblock %}
    {% block business_impact %}{% endblock %}
    {% block recommendations %}{% endblock %}
    {% block appendix %}{% endblock %}
</body>
</html>
```

### 케이스 1: SSL 부재 템플릿
```html
<!-- no_ssl_template.html -->
{% extends "base_template.html" %}

{% block executive_summary %}
<section class="executive-summary">
    <h2>🚨 경영진 요약</h2>
    <div class="critical-alert">
        <h3>치명적 보안 문제 발견</h3>
        <p><strong>{{ domain }}</strong> 웹사이트에 SSL/HTTPS 보안이 전혀 적용되지 않았습니다.</p>
        
        <div class="impact-metrics">
            <div class="metric">
                <span class="number">{{ user_loss_rate }}%</span>
                <span class="label">사용자 이탈률</span>
            </div>
            <div class="metric">
                <span class="number">₩{{ annual_loss | format_currency }}</span>
                <span class="label">연간 예상 손실</span>
            </div>
            <div class="metric">
                <span class="number">{{ seo_penalty }}%</span>
                <span class="label">검색순위 하락</span>
            </div>
        </div>

        <div class="urgent-actions">
            <h4>긴급 조치사항</h4>
            <ul>
                <li>⚡ 즉시: Let's Encrypt 무료 SSL 인증서 설치</li>
                <li>🔒 당일: HTTPS 서비스 활성화 완료</li>
                <li>📈 1주: 트래픽 회복 및 보안 등급 A 달성</li>
            </ul>
        </div>
    </div>
</section>
{% endblock %}

{% block technical_analysis %}
<section class="technical-analysis">
    <h2>🔍 기술적 분석 결과</h2>
    
    <div class="analysis-grid">
        <div class="analysis-item failed">
            <h3>SSL/HTTPS 상태</h3>
            <p class="status">❌ 서비스 없음 (443 포트 닫힘)</p>
            <p>HTTPS 접속 시도 결과: Connection refused</p>
            <code>curl -I https://{{ domain }} → 연결 실패</code>
        </div>

        <div class="analysis-item failed">
            <h3>브라우저 경고</h3>
            <p class="status">⚠️ 모든 브라우저에서 "안전하지 않음" 표시</p>
            <ul>
                <li>Chrome: "안전하지 않음" 경고</li>
                <li>Firefox: 🔓 열린 자물쇠 아이콘</li>
                <li>Safari: "안전하지 않습니다" 메시지</li>
            </ul>
        </div>

        <div class="analysis-item info">
            <h3>현재 HTTP 서비스</h3>
            <p class="status">✅ HTTP는 정상 작동 (포트 80)</p>
            <p>응답 시간: {{ http_response_time }}ms</p>
            <p>서버: {{ server_header }}</p>
        </div>
    </div>

    <div class="security-score-breakdown">
        <h3>보안 점수 세부 사항</h3>
        <div class="score-item">
            <span class="category">SSL/TLS 인증서</span>
            <span class="score">0/40</span>
            <span class="status">인증서 없음</span>
        </div>
        <div class="score-item">
            <span class="category">암호화 강도</span>
            <span class="score">0/25</span>
            <span class="status">암호화 없음</span>
        </div>
        <div class="score-item">
            <span class="category">보안 헤더</span>
            <span class="score">0/20</span>
            <span class="status">HTTPS 필요</span>
        </div>
        <div class="score-item">
            <span class="category">프로토콜 지원</span>
            <span class="score">0/15</span>
            <span class="status">HTTPS 필요</span>
        </div>
        <div class="total-score">
            <span class="category">총 점수</span>
            <span class="score">0/100 (F등급)</span>
        </div>
    </div>
</section>
{% endblock %}

{% block business_impact %}
<section class="business-impact">
    <h2>💰 비즈니스 영향 분석</h2>
    
    <div class="impact-calculation">
        <h3>매출 손실 계산</h3>
        <div class="calculation-steps">
            <div class="step">
                <span class="label">현재 월 방문자</span>
                <span class="value">{{ monthly_visitors | format_number }}명</span>
            </div>
            <div class="step">
                <span class="label">보안 경고 이탈률</span>
                <span class="value">{{ user_loss_rate }}%</span>
            </div>
            <div class="step">
                <span class="label">실제 유효 방문자</span>
                <span class="value">{{ effective_visitors | format_number }}명</span>
            </div>
            <div class="step">
                <span class="label">예상 월 손실</span>
                <span class="value highlight">₩{{ monthly_loss | format_currency }}</span>
            </div>
        </div>
    </div>

    <div class="competitive-analysis">
        <h3>경쟁사 대비 현황</h3>
        <table class="comparison-table">
            <thead>
                <tr>
                    <th>회사</th>
                    <th>SSL 등급</th>
                    <th>보안 점수</th>
                    <th>상태</th>
                </tr>
            </thead>
            <tbody>
                {% for competitor in competitors %}
                <tr>
                    <td>{{ competitor.name }}</td>
                    <td class="grade grade-{{ competitor.grade_class }}">{{ competitor.ssl_grade }}</td>
                    <td>{{ competitor.security_score }}/100</td>
                    <td class="status-{{ competitor.status }}">{{ competitor.status_text }}</td>
                </tr>
                {% endfor %}
                <tr class="current-site">
                    <td><strong>{{ domain }}</strong></td>
                    <td class="grade grade-f">F</td>
                    <td>0/100</td>
                    <td class="status-critical">보안 없음</td>
                </tr>
            </tbody>
        </table>
    </div>
</section>
{% endblock %}

{% block recommendations %}
<section class="recommendations">
    <h2>🔧 해결 방안 및 구현 가이드</h2>
    
    <div class="solution-timeline">
        <h3>단계별 해결 방안</h3>
        
        <div class="phase phase-urgent">
            <div class="phase-header">
                <h4>Phase 1: 긴급 조치 (당일 완료)</h4>
                <span class="duration">소요시간: 2-4시간</span>
                <span class="cost">비용: 0원</span>
            </div>
            <div class="phase-content">
                <h5>Let's Encrypt 무료 SSL 설치</h5>
                <div class="code-block">
                    <h6>Ubuntu/Debian 서버:</h6>
                    <pre><code># Certbot 설치
sudo apt update && apt install snapd
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot

# SSL 인증서 발급 및 설치
sudo certbot --{{ web_server }} -d {{ domain }}

# 자동 갱신 설정  
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -</code></pre>
                </div>
                <div class="expected-result">
                    <h6>당일 완료 후 예상 효과:</h6>
                    <ul>
                        <li>✅ 브라우저 경고 완전 제거</li>
                        <li>✅ 보안 등급 B 달성</li>
                        <li>✅ 사용자 이탈률 80% → 20% 감소</li>
                        <li>✅ 즉시 트래픽 30% 회복</li>
                    </ul>
                </div>
            </div>
        </div>

        <div class="phase phase-important">
            <div class="phase-header">
                <h4>Phase 2: 보안 강화 (1주 이내)</h4>
                <span class="duration">소요시간: 1-2일</span>
                <span class="cost">비용: 0원</span>
            </div>
            <div class="phase-content">
                <h5>SSL 설정 최적화 및 보안 헤더</h5>
                <div class="code-block">
                    <h6>{{ web_server | title }} 보안 설정:</h6>
                    <pre><code>{% if web_server == 'nginx' %}server {
    listen 443 ssl http2;
    server_name {{ domain }};
    
    ssl_certificate /etc/letsencrypt/live/{{ domain }}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{{ domain }}/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
}

# HTTP → HTTPS 리다이렉션
server {
    listen 80;
    server_name {{ domain }};
    return 301 https://$server_name$request_uri;
}{% endif %}</code></pre>
                </div>
                <div class="expected-result">
                    <h6>1주 완료 후 예상 효과:</h6>
                    <ul>
                        <li>✅ SSL Labs A 등급 달성</li>
                        <li>✅ 페이지 로딩 속도 20% 향상</li>
                        <li>✅ SEO 순위 개선 시작</li>
                        <li>✅ 월 매출 {{ improved_monthly_revenue | format_currency }} 회복</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <div class="roi-analysis">
        <h3>투자 대비 효과 (ROI)</h3>
        <div class="roi-metrics">
            <div class="roi-item">
                <span class="label">투자 비용</span>
                <span class="value">₩0 (완전 무료)</span>
            </div>
            <div class="roi-item">
                <span class="label">연간 매출 회복</span>
                <span class="value">₩{{ annual_recovery | format_currency }}</span>
            </div>
            <div class="roi-item">
                <span class="label">ROI</span>
                <span class="value highlight">무한대 (∞%)</span>
            </div>
        </div>
    </div>
</section>
{% endblock %}
```

### 케이스 2: 자체 서명 인증서 템플릿
```html
<!-- self_signed_template.html -->
{% extends "base_template.html" %}

{% block executive_summary %}
<section class="executive-summary">
    <h2>⚠️ 경영진 요약</h2>
    <div class="warning-alert">
        <h3>자체 서명 인증서 문제 발견</h3>
        <p><strong>{{ domain }}</strong> 웹사이트가 자체 서명 인증서를 사용하고 있어 브라우저에서 보안 경고를 표시합니다.</p>
        
        {% if has_406_error %}
        <div class="critical-issue">
            <h4>🚨 추가 서버 설정 문제</h4>
            <p>HTTPS 접속 시 406 Not Acceptable 오류가 발생하여 서비스가 완전히 중단된 상태입니다.</p>
        </div>
        {% endif %}
        
        <div class="impact-metrics">
            <div class="metric">
                <span class="number">{{ user_loss_rate }}%</span>
                <span class="label">사용자 이탈률</span>
            </div>
            <div class="metric">
                <span class="number">₩{{ annual_loss | format_currency }}</span>
                <span class="label">연간 예상 손실</span>
            </div>
            <div class="metric">
                <span class="number">{{ trust_penalty }}%</span>
                <span class="label">브랜드 신뢰도 하락</span>
            </div>
        </div>
    </div>
</section>
{% endblock %}

{% block technical_analysis %}
<section class="technical-analysis">
    <h2>🔍 기술적 분석 결과</h2>
    
    <div class="certificate-details">
        <h3>현재 SSL 인증서 정보</h3>
        <div class="cert-info">
            <div class="cert-field">
                <span class="label">발급 대상 (Subject):</span>
                <span class="value">{{ cert_subject }}</span>
            </div>
            <div class="cert-field">
                <span class="label">발급자 (Issuer):</span>
                <span class="value">{{ cert_issuer }}</span>
            </div>
            <div class="cert-field self-signed-indicator">
                <span class="label">자체 서명 여부:</span>
                <span class="value warning">✅ 자체 서명 (Subject = Issuer)</span>
            </div>
            <div class="cert-field">
                <span class="label">유효 기간:</span>
                <span class="value">{{ cert_valid_from }} ~ {{ cert_valid_to }}</span>
            </div>
        </div>
    </div>

    {% if has_406_error %}
    <div class="server-error-analysis">
        <h3>서버 설정 문제 분석</h3>
        <div class="error-details">
            <div class="error-item critical">
                <span class="status">❌ HTTP 406 Not Acceptable</span>
                <p>HTTPS 접속 시 서버가 요청을 거부하고 있습니다.</p>
            </div>
            <div class="probable-causes">
                <h4>추정 원인:</h4>
                <ul>
                    <li>Accept 헤더 처리 오류</li>
                    <li>프록시 설정 오류</li>
                    <li>PHP 애플리케이션 HTTPS 환경 처리 실패</li>
                    <li>SSL Termination 설정 문제</li>
                </ul>
            </div>
        </div>
    </div>
    {% endif %}

    <div class="browser-impact">
        <h3>브라우저별 경고 상황</h3>
        <div class="browser-warnings">
            <div class="browser-item">
                <span class="browser">Chrome</span>
                <span class="warning">⚠️ "이 연결은 비공개 연결이 아닙니다"</span>
            </div>
            <div class="browser-item">
                <span class="browser">Firefox</span>
                <span class="warning">⚠️ "보안 연결 실패"</span>
            </div>
            <div class="browser-item">
                <span class="browser">Safari</span>
                <span class="warning">⚠️ "이 연결은 안전하지 않습니다"</span>
            </div>
        </div>
    </div>
</section>
{% endblock %}

{% block recommendations %}
<section class="recommendations">
    <h2>🔧 해결 방안 및 구현 가이드</h2>
    
    <div class="solution-priority">
        {% if has_406_error %}
        <div class="phase phase-critical">
            <div class="phase-header">
                <h4>긴급 우선: 서버 설정 수정 (당일 완료)</h4>
                <span class="priority">🚨 최우선</span>
            </div>
            <div class="phase-content">
                <p>HTTPS 서비스를 먼저 정상 작동시킨 후 SSL 인증서를 교체해야 합니다.</p>
                <div class="code-block">
                    <h6>nginx 설정 수정 예시:</h6>
                    <pre><code>server {
    listen 443 ssl http2;
    server_name {{ domain }};
    
    # 현재 인증서 임시 유지
    ssl_certificate /path/to/current.crt;
    ssl_certificate_key /path/to/current.key;
    
    # Accept 헤더 처리 개선
    location / {
        proxy_set_header Accept $http_accept;
        proxy_set_header Host $host;
        proxy_pass http://localhost:8080;
    }
    
    # 406 오류 임시 우회
    error_page 406 = @handle406;
    location @handle406 {
        return 200 "Service temporarily available via HTTP";
    }
}</code></pre>
                </div>
            </div>
        </div>
        {% endif %}
        
        <div class="phase phase-urgent">
            <div class="phase-header">
                <h4>Phase 1: SSL 인증서 교체 (1-2일)</h4>
                <span class="cost">비용: 0원 (Let's Encrypt)</span>
            </div>
            <div class="phase-content">
                <h5>정식 CA 발급 SSL 인증서로 교체</h5>
                <div class="steps">
                    <div class="step">
                        <h6>1. 기존 자체 서명 인증서 백업</h6>
                        <pre><code>sudo cp /path/to/current.crt /path/to/backup/
sudo cp /path/to/current.key /path/to/backup/</code></pre>
                    </div>
                    <div class="step">
                        <h6>2. Let's Encrypt 인증서 발급</h6>
                        <pre><code>sudo certbot --nginx -d {{ domain }}
# 기존 인증서 자동 교체</code></pre>
                    </div>
                    <div class="step">
                        <h6>3. 웹서버 재시작 및 테스트</h6>
                        <pre><code>sudo systemctl reload nginx
curl -I https://{{ domain }}  # 200 OK 확인</code></pre>
                    </div>
                </div>
                
                <div class="expected-result">
                    <h6>완료 후 즉시 효과:</h6>
                    <ul>
                        <li>✅ 모든 브라우저에서 🔒 자물쇠 아이콘 표시</li>
                        <li>✅ 보안 경고 완전 제거</li>
                        <li>✅ SSL Labs B+ 등급 달성</li>
                        <li>✅ 사용자 이탈률 {{ user_loss_rate }}% → 5% 감소</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</section>
{% endblock %}
```

---

## 💻 기술적 구현 세부사항

### 1. Playwright 기반 분석 엔진

#### 메인 분석 클래스
```python
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
import asyncio
from playwright.async_api import async_playwright, Browser, Page
import ssl
import socket
import requests
from datetime import datetime

class SSLCaseType(Enum):
    NO_SSL = "no_ssl"
    SELF_SIGNED = "self_signed" 
    EXPIRED = "expired"
    DOMAIN_MISMATCH = "domain_mismatch"
    VALID = "valid"

@dataclass
class SecurityAnalysisResult:
    domain: str
    case_type: SSLCaseType
    security_grade: str
    security_score: int
    ssl_details: Dict
    server_issues: Dict
    browser_analysis: Dict  # 브라우저별 실제 경고 정보
    performance_data: Dict
    screenshots: Dict  # 경고 화면 스크린샷
    business_impact: Dict
    recommendations: List[Dict]
    analysis_timestamp: datetime

class PlaywrightSecurityAnalyzer:
    """Playwright 기반 보안 분석기"""
    
    def __init__(self):
        self.timeout = 30000  # 30초
        self.user_agent = "SecureCheck Pro Analyzer/1.0"
        self.browsers = ['chromium', 'firefox', 'webkit']
    
    async def analyze_website(self, domain: str) -> SecurityAnalysisResult:
        """메인 분석 메소드 - Playwright로 실제 브라우저 테스트"""
        
        async with async_playwright() as p:
            # Step 1: 네트워크 레벨 기본 체크 (SSL 존재 여부)
            network_check = await self._check_network_connectivity(domain)
            
            if not network_check['has_ssl']:
                return await self._analyze_no_ssl_scenario(domain, network_check)
            
            # Step 2: 브라우저별 실제 접속 테스트 (Playwright)
            browser_results = await self._test_all_browsers(p, domain)
            
            # Step 3: SSL 인증서 세부 분석 (OpenSSL)
            cert_details = await self._analyze_certificate_details(domain)
            
            # Step 4: 시나리오 분류 및 종합 분석
            scenario = self._classify_security_scenario(network_check, browser_results, cert_details)
            
            return await self._compile_scenario_result(domain, scenario, browser_results, cert_details)
    
    async def _test_all_browsers(self, playwright, domain: str) -> Dict:
        """모든 브라우저에서 실제 접속 테스트"""
        browser_results = {}
        
        for browser_type in self.browsers:
            try:
                browser = await getattr(playwright, browser_type).launch(
                    headless=True,
                    args=['--ignore-certificate-errors-spki-list',
                          '--ignore-ssl-errors',
                          '--allow-running-insecure-content']
                )
                
                page = await browser.new_page()
                await page.set_user_agent(self.user_agent)
                
                # 각 브라우저별 시나리오 실행
                result = await self._execute_browser_scenario(page, domain, browser_type)
                browser_results[browser_type] = result
                
                await browser.close()
                
            except Exception as e:
                browser_results[browser_type] = {'error': str(e), 'status': 'failed'}
        
        return browser_results
    
    async def _execute_browser_scenario(self, page: Page, domain: str, browser_type: str) -> Dict:
        """브라우저별 접속 시나리오 실행"""
        scenario_result = {
            'browser': browser_type,
            'https_attempt': {},
            'http_attempt': {},
            'security_warnings': [],
            'screenshots': {},
            'performance_metrics': {}
        }
        
        # 시나리오 1: HTTPS 접속 시도
        https_result = await self._test_https_connection(page, domain)
        scenario_result['https_attempt'] = https_result
        
        # 시나리오 2: HTTP 접속 시도 (대조군)
        http_result = await self._test_http_connection(page, domain)
        scenario_result['http_attempt'] = http_result
        
        # 시나리오 3: 보안 경고 감지 및 스크린샷
        if https_result.get('has_security_warning'):
            warning_details = await self._capture_security_warnings(page, domain)
            scenario_result['security_warnings'] = warning_details
        
        return scenario_result
    
    async def _test_https_connection(self, page: Page, domain: str) -> Dict:
        """HTTPS 연결 테스트 시나리오"""
        result = {
            'attempted': True,
            'url': f'https://{domain}',
            'success': False,
            'status_code': None,
            'error_type': None,
            'security_warning': None,
            'response_time': None,
            'screenshot_path': None
        }
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # 페이지 접속 시도
            response = await page.goto(f'https://{domain}', 
                                     wait_until='domcontentloaded',
                                     timeout=self.timeout)
            
            end_time = asyncio.get_event_loop().time()
            result['response_time'] = (end_time - start_time) * 1000  # ms
            
            if response:
                result['success'] = True
                result['status_code'] = response.status
                
                # 보안 경고 감지
                warning = await self._detect_security_warning(page, domain)
                if warning:
                    result['security_warning'] = warning
                    result['has_security_warning'] = True
                    
                    # 경고 화면 스크린샷
                    screenshot_path = await self._take_warning_screenshot(page, domain)
                    result['screenshot_path'] = screenshot_path
            
        except Exception as e:
            result['success'] = False
            result['error_type'] = type(e).__name__
            result['error_message'] = str(e)
            
            # 에러 화면도 스크린샷
            try:
                screenshot_path = await self._take_error_screenshot(page, domain, str(e))
                result['screenshot_path'] = screenshot_path
            except:
                pass
        
        return result
    
    async def _detect_security_warning(self, page: Page, domain: str) -> Optional[Dict]:
        """브라우저별 보안 경고 감지"""
        warning_selectors = {
            'chromium': [
                'text="Your connection is not private"',
                'text="This site can\'t provide a secure connection"',
                'text="안전하지 않음"',
                '[data-error-code="SSL_VERSION_OR_CIPHER_MISMATCH"]',
                '.security-interstitial-wrapper'
            ],
            'firefox': [
                'text="Secure Connection Failed"', 
                'text="보안 연결 실패"',
                '.certerror',
                '#errorShortDesc'
            ],
            'webkit': [
                'text="This Connection Is Not Private"',
                'text="이 연결은 안전하지 않습니다"',
                '.error-page'
            ]
        }
        
        browser_type = page.browser().browser_type.name
        selectors = warning_selectors.get(browser_type, warning_selectors['chromium'])
        
        for selector in selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=3000)
                if element:
                    warning_text = await element.text_content()
                    return {
                        'detected': True,
                        'selector_matched': selector,
                        'warning_text': warning_text,
                        'browser_type': browser_type,
                        'warning_category': self._categorize_warning(warning_text)
                    }
            except:
                continue
        
        return None
    
    def _categorize_warning(self, warning_text: str) -> str:
        """경고 메시지 카테고리 분류"""
        warning_text_lower = warning_text.lower()
        
        if any(term in warning_text_lower for term in ['expired', '만료']):
            return 'expired_certificate'
        elif any(term in warning_text_lower for term in ['private', '비공개', 'authority', '기관']):
            return 'untrusted_certificate'  # 자체서명 등
        elif any(term in warning_text_lower for term in ['secure', '보안', 'connection', '연결']):
            return 'connection_not_secure'  # SSL 없음
        else:
            return 'unknown_ssl_error'
    
    async def _take_warning_screenshot(self, page: Page, domain: str) -> str:
        """보안 경고 화면 스크린샷 캡처"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"security_warning_{domain}_{timestamp}.png"
        screenshot_path = f"screenshots/{filename}"
        
        await page.screenshot(path=screenshot_path, full_page=True)
        return screenshot_path

class BrowserScenarioRunner:
    """브라우저별 사전 정의된 시나리오 실행기"""
    
    def __init__(self):
        self.scenarios = self._load_predefined_scenarios()
    
    def _load_predefined_scenarios(self) -> Dict:
        """사전 정의된 시나리오 스크립트들"""
        return {
            'ssl_status_check': {
                'description': 'SSL 인증서 상태 및 브라우저 반응 확인',
                'steps': [
                    {'action': 'navigate', 'url': 'https://{domain}'},
                    {'action': 'wait_for_load', 'timeout': 10000},
                    {'action': 'detect_warnings', 'selectors': 'security_warning_selectors'},
                    {'action': 'capture_screenshot', 'name': 'ssl_status'},
                    {'action': 'check_address_bar', 'look_for': 'lock_icon'},
                    {'action': 'measure_performance', 'metrics': ['load_time', 'dom_ready']}
                ]
            },
            'form_interaction_test': {
                'description': '폼 입력시 추가 보안 경고 확인',
                'steps': [
                    {'action': 'navigate', 'url': 'https://{domain}'},
                    {'action': 'find_forms', 'types': ['input[type="email"]', 'input[type="password"]']},
                    {'action': 'interact_with_form', 'simulate_typing': True},
                    {'action': 'detect_additional_warnings', 'context': 'form_interaction'},
                    {'action': 'capture_screenshot', 'name': 'form_warning'}
                ]
            },
            'mobile_browser_test': {
                'description': '모바일 환경에서의 보안 경고 테스트',
                'device': 'iPhone 12',
                'steps': [
                    {'action': 'set_mobile_viewport'},
                    {'action': 'navigate', 'url': 'https://{domain}'},
                    {'action': 'detect_mobile_warnings', 'stricter': True},
                    {'action': 'capture_screenshot', 'name': 'mobile_warning'},
                    {'action': 'test_mobile_bypass', 'check_difficulty': True}
                ]
            },
            'cross_browser_comparison': {
                'description': '브라우저별 보안 경고 차이점 분석',
                'browsers': ['chromium', 'firefox', 'webkit'],
                'steps': [
                    {'action': 'parallel_browser_test'},
                    {'action': 'compare_warning_messages'},
                    {'action': 'analyze_bypass_complexity'},
                    {'action': 'measure_user_friction'}
                ]
            }
        }
    
    async def run_scenario(self, scenario_name: str, domain: str, browser_type: str = 'chromium') -> Dict:
        """특정 시나리오 실행"""
        if scenario_name not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        
        scenario = self.scenarios[scenario_name]
        results = {
            'scenario_name': scenario_name,
            'description': scenario['description'],
            'browser_type': browser_type,
            'steps_completed': [],
            'screenshots': [],
            'warnings_detected': [],
            'performance_metrics': {},
            'success': False
        }
        
        async with async_playwright() as p:
            browser = await getattr(p, browser_type).launch(
                headless=True,
                args=['--ignore-certificate-errors'] if scenario_name == 'ssl_status_check' else []
            )
            
            # 모바일 테스트인 경우 디바이스 설정
            if scenario.get('device'):
                device = p.devices[scenario['device']]
                context = await browser.new_context(**device)
            else:
                context = await browser.new_context()
            
            page = await context.new_page()
            
            # 시나리오 단계별 실행
            for step in scenario['steps']:
                try:
                    step_result = await self._execute_step(page, step, domain)
                    results['steps_completed'].append({
                        'step': step,
                        'result': step_result,
                        'success': True
                    })
                except Exception as e:
                    results['steps_completed'].append({
                        'step': step,
                        'error': str(e),
                        'success': False
                    })
            
            await browser.close()
        
        results['success'] = len([s for s in results['steps_completed'] if s['success']]) > 0
        return results
    
    async def _execute_step(self, page: Page, step: Dict, domain: str) -> Dict:
        """시나리오 스텝 실행"""
        action = step['action']
        
        if action == 'navigate':
            url = step['url'].format(domain=domain)
            response = await page.goto(url, timeout=30000)
            return {
                'action': 'navigate',
                'url': url,
                'status_code': response.status if response else None,
                'load_time': await self._measure_load_time(page)
            }
        
        elif action == 'detect_warnings':
            warnings = await self._scan_for_warnings(page)
            return {
                'action': 'detect_warnings',
                'warnings_found': warnings,
                'warning_count': len(warnings)
            }
        
        elif action == 'capture_screenshot':
            screenshot_path = await self._capture_scenario_screenshot(page, domain, step['name'])
            return {
                'action': 'capture_screenshot',
                'screenshot_path': screenshot_path
            }
        
        elif action == 'check_address_bar':
            address_bar_info = await self._analyze_address_bar(page)
            return {
                'action': 'check_address_bar', 
                'address_bar_info': address_bar_info
            }
        
        elif action == 'find_forms':
            forms = await self._find_form_elements(page, step.get('types', []))
            return {
                'action': 'find_forms',
                'forms_found': forms,
                'form_count': len(forms)
            }
        
        elif action == 'interact_with_form':
            interaction_result = await self._simulate_form_interaction(page)
            return {
                'action': 'interact_with_form',
                'interaction_result': interaction_result
            }
        
        elif action == 'measure_performance':
            performance = await self._measure_page_performance(page)
            return {
                'action': 'measure_performance',
                'metrics': performance
            }
        
        else:
            return {'action': action, 'status': 'not_implemented'}
    
    async def _scan_for_warnings(self, page: Page) -> List[Dict]:
        """페이지에서 보안 경고 스캔"""
        warnings = []
        
        # 일반적인 SSL 경고 셀렉터들
        warning_patterns = [
            # Chrome/Chromium
            {
                'selector': '.security-interstitial-wrapper',
                'type': 'ssl_interstitial',
                'severity': 'critical'
            },
            {
                'selector': '[data-error-code]',
                'type': 'ssl_error_code',
                'severity': 'critical'
            },
            # Firefox  
            {
                'selector': '.certerror',
                'type': 'certificate_error',
                'severity': 'critical'
            },
            {
                'selector': '#errorShortDesc',
                'type': 'connection_error',
                'severity': 'critical'
            },
            # Safari/WebKit
            {
                'selector': '.error-page',
                'type': 'generic_error',
                'severity': 'warning'
            },
            # 공통
            {
                'selector': 'text=안전하지 않',
                'type': 'korean_security_warning',
                'severity': 'warning'
            },
            {
                'selector': 'text=connection is not private',
                'type': 'privacy_warning', 
                'severity': 'warning'
            }
        ]
        
        for pattern in warning_patterns:
            try:
                elements = await page.query_selector_all(pattern['selector'])
                for element in elements:
                    text_content = await element.text_content()
                    warnings.append({
                        'type': pattern['type'],
                        'severity': pattern['severity'],
                        'selector': pattern['selector'],
                        'text': text_content,
                        'visible': await element.is_visible()
                    })
            except:
                continue
        
        return warnings
    
    async def _analyze_address_bar(self, page: Page) -> Dict:
        """주소창 보안 상태 분석 (브라우저별)"""
        try:
            # 페이지 URL과 보안 상태 확인
            current_url = page.url
            
            # JavaScript로 브라우저 보안 정보 추출 시도
            security_info = await page.evaluate('''() => {
                return {
                    url: window.location.href,
                    protocol: window.location.protocol,
                    host: window.location.host,
                    isSecure: window.isSecureContext,
                    connection: navigator.connection ? {
                        effectiveType: navigator.connection.effectiveType,
                        downlink: navigator.connection.downlink
                    } : null
                };
            }''')
            
            return {
                'current_url': current_url,
                'is_https': current_url.startswith('https://'),
                'is_secure_context': security_info.get('isSecure', False),
                'protocol': security_info.get('protocol'),
                'security_state': self._determine_security_state(current_url, security_info)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _determine_security_state(self, url: str, security_info: Dict) -> str:
        """브라우저 보안 상태 결정"""
        if not url.startswith('https://'):
            return 'not_secure'
        elif not security_info.get('isSecure', False):
            return 'insecure_https'  # HTTPS이지만 브라우저가 안전하지 않다고 판단
        else:
            return 'secure'
    
    async def _simulate_form_interaction(self, page: Page) -> Dict:
        """폼 상호작용 시뮬레이션 (보안 경고 추가 발생 여부)"""
        interaction_result = {
            'forms_found': 0,
            'interactions_attempted': 0,
            'additional_warnings': [],
            'input_blocked': False
        }
        
        try:
            # 이메일/패스워드 입력 필드 찾기
            email_inputs = await page.query_selector_all('input[type="email"], input[name*="email"], input[id*="email"]')
            password_inputs = await page.query_selector_all('input[type="password"]')
            
            interaction_result['forms_found'] = len(email_inputs) + len(password_inputs)
            
            # 실제 입력 시뮬레이션
            if email_inputs:
                for email_input in email_inputs[:2]:  # 최대 2개만 테스트
                    try:
                        await email_input.click()
                        await email_input.fill('test@example.com')
                        interaction_result['interactions_attempted'] += 1
                        
                        # 입력 후 추가 경고 확인
                        additional_warnings = await self._scan_for_warnings(page)
                        if additional_warnings:
                            interaction_result['additional_warnings'].extend(additional_warnings)
                    except Exception as e:
                        if 'blocked' in str(e).lower():
                            interaction_result['input_blocked'] = True
            
            # 패스워드 필드도 동일하게 테스트
            if password_inputs:
                for pwd_input in password_inputs[:1]:
                    try:
                        await pwd_input.click()
                        await pwd_input.fill('test123!')
                        interaction_result['interactions_attempted'] += 1
                    except Exception as e:
                        if 'blocked' in str(e).lower():
                            interaction_result['input_blocked'] = True
            
        except Exception as e:
            interaction_result['error'] = str(e)
        
        return interaction_result

class NetworkAnalyzer:
    """네트워크 레벨 SSL 분석 (OpenSSL + Python)"""
    
    @staticmethod
    async def analyze_ssl_certificate(domain: str) -> Dict:
        """SSL 인증서 상세 분석"""
        try:
            # 포트 443 연결 가능성 먼저 확인
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            connection_result = sock.connect_ex((domain, 443))
            sock.close()
            
            if connection_result != 0:
                return {
                    'status': 'no_ssl',
                    'port_443_open': False,
                    'error': 'Connection refused'
                }
            
            # SSL 인증서 정보 추출
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((domain, 443), timeout=30) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    protocol_version = ssock.version()
                    cipher = ssock.cipher()
            
            # 인증서 분석
            cert_analysis = NetworkAnalyzer._analyze_certificate_details(cert, domain)
            
            return {
                'status': 'has_ssl',
                'port_443_open': True,
                'certificate': cert_analysis,
                'tls_version': protocol_version,
                'cipher_info': cipher,
                'case_type': cert_analysis['case_type']
            }
            
        except ssl.SSLError as e:
            return {
                'status': 'ssl_error',
                'port_443_open': True,
                'ssl_error': str(e),
                'error_type': 'ssl_handshake_failed'
            }
        except Exception as e:
            return {
                'status': 'connection_error',
                'error': str(e)
            }
    
    @staticmethod
    def _analyze_certificate_details(cert: Dict, domain: str) -> Dict:
        """인증서 세부 분석"""
        subject = dict(x[0] for x in cert['subject'])
        issuer = dict(x[0] for x in cert['issuer'])
        
        # 케이스 분류
        if subject == issuer:
            case_type = 'self_signed'
        else:
            # 만료 체크
            not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
            if not_after < datetime.utcnow():
                case_type = 'expired'
            else:
                # 도메인 매칭 체크
                cert_domains = NetworkAnalyzer._extract_domains_from_cert(cert)
                if domain not in cert_domains and not NetworkAnalyzer._wildcard_match(domain, cert_domains):
                    case_type = 'domain_mismatch'
                else:
                    case_type = 'valid'
        
        return {
            'case_type': case_type,
            'subject': subject,
            'issuer': issuer,
            'not_before': cert['notBefore'],
            'not_after': cert['notAfter'], 
            'serial_number': cert['serialNumber'],
            'version': cert['version'],
            'san_domains': cert.get('subjectAltName', []),
            'is_self_signed': subject == issuer,
            'days_until_expiry': (datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z') - datetime.utcnow()).days
        }

class ScenarioBasedReportGenerator:
    """시나리오 기반 보고서 생성기 (AI 제외)"""
    
    def __init__(self):
        self.template_env = self._setup_jinja_environment()
        self.scenario_templates = self._load_scenario_templates()
    
    def _load_scenario_templates(self) -> Dict:
        """시나리오별 고정 템플릿 매핑"""
        return {
            # 기본 SSL 케이스
            'no_ssl': 'no_ssl_template.html',
            'self_signed': 'self_signed_template.html', 
            'expired': 'expired_template.html',
            'domain_mismatch': 'domain_mismatch_template.html',
            'valid': 'valid_ssl_template.html',
            
            # 복합 문제 케이스 (서버 오류 + SSL 문제)
            'self_signed_with_406': 'self_signed_406_template.html',
            'self_signed_with_500': 'self_signed_500_template.html',
            'expired_with_502': 'expired_502_template.html',
            
            # 특별 케이스
            'ssl_but_no_headers': 'ssl_no_headers_template.html',
            'perfect_ssl_setup': 'perfect_ssl_template.html'
        }
    
    def generate_scenario_report(self, analysis_result: SecurityAnalysisResult) -> str:
        """시나리오 기반 보고서 생성"""
        
        # 시나리오 정확히 식별
        scenario_key = self._identify_exact_scenario(analysis_result)
        
        # 해당 시나리오 템플릿 로드
        template_name = self.scenario_templates.get(scenario_key, 'default_template.html')
        template = self.template_env.get_template(template_name)
        
        # 시나리오별 고정 데이터 준비
        template_data = self._prepare_scenario_data(analysis_result, scenario_key)
        
        # HTML 렌더링
        html_content = template.render(**template_data)
        
        # PDF 생성
        pdf_path = self._generate_scenario_pdf(html_content, analysis_result.domain, scenario_key)
        
        return pdf_path
    
    def _identify_exact_scenario(self, result: SecurityAnalysisResult) -> str:
        """정확한 시나리오 식별 (복합 문제 고려)"""
        base_case = result.case_type.value
        
        # 서버 오류가 있는지 확인
        if result.server_issues.get('status_code'):
            status_code = result.server_issues['status_code']
            if status_code != 200:
                return f"{base_case}_with_{status_code}"
        
        # 특별한 조합 케이스 확인
        if base_case == 'valid':
            headers_score = result.ssl_details.get('headers_score', 0)
            if headers_score == 0:
                return 'ssl_but_no_headers'
            elif result.security_score >= 95:
                return 'perfect_ssl_setup'
        
        return base_case
    
    def _prepare_scenario_data(self, result: SecurityAnalysisResult, scenario_key: str) -> Dict:
        """시나리오별 고정 템플릿 데이터 준비"""
        base_data = {
            'domain': result.domain,
            'scenario_key': scenario_key,
            'analysis_date': result.analysis_timestamp.strftime('%Y년 %m월 %d일'),
            'report_date': datetime.now().strftime('%Y년 %m월 %d일 %H:%M'),
            'security_grade': result.security_grade,
            'security_score': result.security_score,
            'grade_class': result.security_grade.lower().replace('+', 'plus'),
            'ssl_case_type': result.case_type.value,
        }
        
        # 시나리오별 특화 데이터 추가
        scenario_data = getattr(self, f'_prepare_{scenario_key}_data', self._prepare_default_data)
        base_data.update(scenario_data(result))
        
        return base_data
    
    def _prepare_no_ssl_data(self, result: SecurityAnalysisResult) -> Dict:
        """SSL 부재 시나리오 데이터"""
        return {
            'severity': 'critical',
            'alert_title': '치명적 보안 문제 발견',
            'alert_message': f'{result.domain} 웹사이트에 SSL/HTTPS 보안이 전혀 적용되지 않았습니다.',
            'user_loss_rate': result.business_impact['user_loss_rate'],
            'annual_loss': result.business_impact['annual_loss'],
            'seo_penalty': result.business_impact.get('seo_penalty', 40),
            'trust_damage': result.business_impact.get('trust_damage', 90),
            'urgent_actions': self._get_no_ssl_actions(),
            'issues_count': 4,  # SSL, 헤더, 프로토콜, 암호화 모두 문제
            'estimated_fix_time': '2-4시간',
            'estimated_cost': 0,
            'hourly_loss': result.business_impact['annual_loss'] / (365 * 24),
            'daily_loss': result.business_impact['annual_loss'] / 365,
            'weekly_loss': result.business_impact['annual_loss'] / 52,
            'monthly_loss': result.business_impact['annual_loss'] / 12
        }
    
    def _get_no_ssl_actions(self) -> List[Dict]:
        """SSL 부재 케이스 고정 액션 플랜"""
        return [
            {
                'priority': 'critical',
                'timeframe': '당일',
                'title': 'Let\'s Encrypt 무료 SSL 인증서 설치',
                'description': 'SSL 인증서 즉시 설치로 보안 경고 제거',
                'expected_impact': '보안 등급 F → B, 이탈률 80% → 20%'
            },
            {
                'priority': 'high', 
                'timeframe': '1주일',
                'title': 'HTTPS 리다이렉션 및 보안 강화',
                'description': 'SSL Labs A등급 달성 및 완전한 HTTPS 전환',
                'expected_impact': '월 매출 회복 및 검색 순위 개선'
            }
        ]
        
        # Step 1: 기본 연결 및 SSL 존재 여부 확인
        has_ssl = await self._check_ssl_availability(domain)
        
        if not has_ssl:
            return await self._analyze_no_ssl_case(domain)
        
        # Step 2: SSL 인증서 상세 정보 추출
        cert_info = await self._extract_certificate_info(domain)
        
        # Step 3: 케이스 분류
        case_type = self._classify_ssl_case(domain, cert_info)
        
        # Step 4: 케이스별 상세 분석
        if case_type == SSLCaseType.SELF_SIGNED:
            return await self._analyze_self_signed_case(domain, cert_info)
        elif case_type == SSLCaseType.EXPIRED:
            return await self._analyze_expired_case(domain, cert_info)
        elif case_type == SSLCaseType.DOMAIN_MISMATCH:
            return await self._analyze_domain_mismatch_case(domain, cert_info)
        else:
            return await self._analyze_valid_ssl_case(domain, cert_info)
    
    async def _check_ssl_availability(self, domain: str) -> bool:
        """SSL 서비스 가용성 확인"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((domain, 443))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    async def _extract_certificate_info(self, domain: str) -> Dict:
        """SSL 인증서 정보 추출"""
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((domain, 443), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    
            return {
                'subject': dict(x[0] for x in cert['subject']),
                'issuer': dict(x[0] for x in cert['issuer']),
                'version': cert['version'],
                'serial_number': cert['serialNumber'],
                'not_before': cert['notBefore'],
                'not_after': cert['notAfter'],
                'san': cert.get('subjectAltName', [])
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _classify_ssl_case(self, domain: str, cert_info: Dict) -> SSLCaseType:
        """SSL 케이스 분류 로직"""
        if 'error' in cert_info:
            return SSLCaseType.NO_SSL
        
        # 자체 서명 여부 확인
        if cert_info['subject'] == cert_info['issuer']:
            return SSLCaseType.SELF_SIGNED
        
        # 만료 여부 확인
        expiry_date = datetime.strptime(cert_info['not_after'], '%b %d %H:%M:%S %Y %Z')
        if expiry_date < datetime.utcnow():
            return SSLCaseType.EXPIRED
        
        # 도메인 일치 여부 확인
        cert_domains = self._extract_cert_domains(cert_info)
        if domain not in cert_domains and not self._wildcard_match(domain, cert_domains):
            return SSLCaseType.DOMAIN_MISMATCH
        
        return SSLCaseType.VALID
    
    async def _analyze_no_ssl_case(self, domain: str) -> SecurityAnalysisResult:
        """SSL 부재 케이스 분석"""
        # HTTP 서비스 확인
        http_info = await self._check_http_service(domain)
        
        # 비즈니스 영향 계산
        business_impact = self._calculate_no_ssl_impact(domain)
        
        return SecurityAnalysisResult(
            domain=domain,
            case_type=SSLCaseType.NO_SSL,
            security_grade='F',
            security_score=0,
            ssl_details={'status': 'no_ssl', 'port_443_open': False},
            server_issues=http_info,
            business_impact=business_impact,
            recommendations=self._get_no_ssl_recommendations(),
            analysis_timestamp=datetime.utcnow()
        )
    
    async def _analyze_self_signed_case(self, domain: str, cert_info: Dict) -> SecurityAnalysisResult:
        """자체 서명 케이스 분석"""
        # 서버 응답 테스트 (406 오류 확인)
        server_response = await self._test_https_response(domain)
        
        # 비즈니스 영향 계산
        business_impact = self._calculate_self_signed_impact(domain, server_response)
        
        return SecurityAnalysisResult(
            domain=domain,
            case_type=SSLCaseType.SELF_SIGNED,
            security_grade='D',
            security_score=25,
            ssl_details={
                'cert_info': cert_info,
                'is_self_signed': True,
                'subject_issuer_match': cert_info['subject'] == cert_info['issuer']
            },
            server_issues=server_response,
            business_impact=business_impact,
            recommendations=self._get_self_signed_recommendations(server_response),
            analysis_timestamp=datetime.utcnow()
        )
    
    def _calculate_no_ssl_impact(self, domain: str) -> Dict:
        """SSL 부재 시 비즈니스 영향 계산"""
        # 기본 가정값들 (실제로는 웹사이트 규모에 따라 조정)
        estimated_monthly_visitors = 5000
        user_loss_rate = 0.8  # 80% 이탈
        conversion_rate = 0.015
        order_conversion_rate = 0.08
        average_order_value = 20000000  # 2천만원
        
        effective_visitors = estimated_monthly_visitors * (1 - user_loss_rate)
        lost_visitors = estimated_monthly_visitors - effective_visitors
        
        monthly_loss = lost_visitors * conversion_rate * order_conversion_rate * average_order_value
        annual_loss = monthly_loss * 12
        
        return {
            'monthly_visitors': estimated_monthly_visitors,
            'user_loss_rate': user_loss_rate * 100,
            'lost_visitors_monthly': lost_visitors,
            'monthly_revenue_loss': monthly_loss,
            'annual_revenue_loss': annual_loss,
            'seo_penalty_percentage': 40,
            'trust_damage_percentage': 90
        }
    
    def _get_no_ssl_recommendations(self) -> List[Dict]:
        """SSL 부재 케이스 권장사항"""
        return [
            {
                'priority': 'critical',
                'title': 'Let\'s Encrypt 무료 SSL 인증서 설치',
                'description': '즉시 Let\'s Encrypt를 사용하여 무료 SSL 인증서를 설치하세요.',
                'implementation_time': '2-4시간',
                'cost': 0,
                'commands': [
                    'sudo apt update && apt install snapd',
                    'sudo snap install --classic certbot',
                    'sudo certbot --nginx -d {domain}',
                    'echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -'
                ],
                'expected_impact': {
                    'security_grade_improvement': 'F → B',
                    'user_retention_improvement': '+60%',
                    'immediate_traffic_recovery': '+30%'
                }
            },
            {
                'priority': 'high',
                'title': 'HTTPS 리다이렉션 설정',
                'description': 'HTTP 접속을 자동으로 HTTPS로 리다이렉션하도록 설정하세요.',
                'implementation_time': '30분',
                'cost': 0
            },
            {
                'priority': 'medium',
                'title': '보안 헤더 적용',
                'description': 'HSTS, X-Frame-Options 등 추가 보안 헤더를 적용하세요.',
                'implementation_time': '1-2시간',
                'cost': 0
            }
        ]

# 웹서버 감지 및 설정 템플릿 생성
class WebServerDetector:
    @staticmethod
    async def detect_web_server(domain: str) -> str:
        """웹서버 종류 감지"""
        try:
            response = requests.get(f'http://{domain}', timeout=10)
            server_header = response.headers.get('Server', '').lower()
            
            if 'nginx' in server_header:
                return 'nginx'
            elif 'apache' in server_header:
                return 'apache'
            else:
                return 'unknown'
        except:
            return 'unknown'
    
    @staticmethod
    def get_ssl_config_template(web_server: str, domain: str) -> str:
        """웹서버별 SSL 설정 템플릿 반환"""
        if web_server == 'nginx':
            return f"""server {{
    listen 443 ssl http2;
    server_name {domain};
    
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
}}

server {{
    listen 80;
    server_name {domain};
    return 301 https://$server_name$request_uri;
}}"""
        elif web_server == 'apache':
            return f"""<VirtualHost *:443>
    ServerName {domain}
    DocumentRoot /var/www/html
    
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/{domain}/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/{domain}/privkey.pem
    
    SSLProtocol All -SSLv3 -TLSv1 -TLSv1.1
    SSLCipherSuite ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512
    
    Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
    Header always set X-Frame-Options DENY
    Header always set X-Content-Type-Options nosniff
</VirtualHost>

<VirtualHost *:80>
    ServerName {domain}
    Redirect permanent / https://{domain}/
</VirtualHost>"""
        else:
            return "# 웹서버를 감지할 수 없습니다. 수동 설정이 필요합니다."
```

### 2. 보고서 생성 엔진

#### 템플릿 기반 보고서 생성기
```python
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
import os
from datetime import datetime

class ReportGenerator:
    def __init__(self, template_dir: str = "templates"):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template_dir = template_dir
        
        # 커스텀 필터 등록
        self.env.filters['format_currency'] = self._format_currency
        self.env.filters['format_number'] = self._format_number
        self.env.filters['format_percentage'] = self._format_percentage
    
    def generate_report(self, analysis_result: SecurityAnalysisResult) -> str:
        """분석 결과를 바탕으로 PDF 보고서 생성"""
        
        # 케이스별 템플릿 선택
        template_name = self._get_template_name(analysis_result.case_type)
        template = self.env.get_template(template_name)
        
        # 템플릿에 전달할 데이터 준비
        template_data = self._prepare_template_data(analysis_result)
        
        # HTML 렌더링
        html_content = template.render(**template_data)
        
        # PDF 생성
        pdf_path = self._generate_pdf(html_content, analysis_result.domain)
        
        return pdf_path
    
    def _get_template_name(self, case_type: SSLCaseType) -> str:
        """케이스별 템플릿 파일명 반환"""
        template_map = {
            SSLCaseType.NO_SSL: 'no_ssl_template.html',
            SSLCaseType.SELF_SIGNED: 'self_signed_template.html',
            SSLCaseType.EXPIRED: 'expired_cert_template.html',
            SSLCaseType.DOMAIN_MISMATCH: 'domain_mismatch_template.html',
            SSLCaseType.VALID: 'valid_ssl_template.html'
        }
        return template_map.get(case_type, 'default_template.html')
    
    def _prepare_template_data(self, result: SecurityAnalysisResult) -> Dict:
        """템플릿에 전달할 데이터 준비"""
        base_data = {
            'domain': result.domain,
            'analysis_date': result.analysis_timestamp.strftime('%Y년 %m월 %d일'),
            'report_date': datetime.now().strftime('%Y년 %m월 %d일 %H:%M'),
            'security_grade': result.security_grade,
            'security_score': result.security_score,
            'grade_class': result.security_grade.lower().replace('+', 'plus'),
            'case_type': result.case_type.value,
        }
        
        # 케이스별 추가 데이터
        if result.case_type == SSLCaseType.NO_SSL:
            base_data.update(self._prepare_no_ssl_data(result))
        elif result.case_type == SSLCaseType.SELF_SIGNED:
            base_data.update(self._prepare_self_signed_data(result))
        
        return base_data
    
    def _prepare_no_ssl_data(self, result: SecurityAnalysisResult) -> Dict:
        """SSL 부재 케이스 템플릿 데이터"""
        impact = result.business_impact
        
        return {
            'user_loss_rate': impact['user_loss_rate'],
            'annual_loss': impact['annual_revenue_loss'],
            'seo_penalty': impact['seo_penalty_percentage'],
            'monthly_visitors': impact['monthly_visitors'],
            'lost_visitors': impact['lost_visitors_monthly'],
            'monthly_loss': impact['monthly_revenue_loss'],
            'http_response_time': result.server_issues.get('response_time', 'N/A'),
            'server_header': result.server_issues.get('server', 'Unknown'),
            'web_server': self._detect_web_server_type(result.server_issues),
            'competitors': self._get_competitor_data(),
            'annual_recovery': impact['annual_revenue_loss'],  # 회복 예상 금액
            'improved_monthly_revenue': impact['monthly_revenue_loss'] + (impact['monthly_visitors'] * 0.015 * 0.08 * 20000000)
        }
    
    def _prepare_self_signed_data(self, result: SecurityAnalysisResult) -> Dict:
        """자체 서명 케이스 템플릿 데이터"""
        ssl_details = result.ssl_details
        cert_info = ssl_details.get('cert_info', {})
        
        return {
            'cert_subject': self._format_cert_subject(cert_info.get('subject', {})),
            'cert_issuer': self._format_cert_subject(cert_info.get('issuer', {})),
            'cert_valid_from': cert_info.get('not_before', 'Unknown'),
            'cert_valid_to': cert_info.get('not_after', 'Unknown'),
            'has_406_error': result.server_issues.get('status_code') == 406,
            'response_time': result.server_issues.get('response_time', 0),
            'user_loss_rate': result.business_impact.get('user_loss_rate', 50),
            'annual_loss': result.business_impact.get('annual_revenue_loss', 0),
            'trust_penalty': result.business_impact.get('trust_damage_percentage', 60)
        }
    
    def _generate_pdf(self, html_content: str, domain: str) -> str:
        """HTML을 PDF로 변환"""
        # CSS 스타일 로드
        css_file = os.path.join(self.template_dir, 'report_styles.css')
        
        # PDF 파일 경로
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"{domain.replace('.', '_')}_security_report_{timestamp}.pdf"
        pdf_path = os.path.join('reports', pdf_filename)
        
        # 디렉토리 생성
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        
        # PDF 생성
        HTML(string=html_content).write_pdf(
            pdf_path,
            stylesheets=[CSS(css_file)] if os.path.exists(css_file) else None
        )
        
        return pdf_path
    
    @staticmethod
    def _format_currency(amount: float) -> str:
        """통화 형식 포맷팅"""
        if amount >= 100000000:  # 1억 이상
            return f"{amount/100000000:.1f}억원"
        elif amount >= 10000:  # 1만 이상
            return f"{amount/10000:.0f}만원"
        else:
            return f"{amount:,.0f}원"
    
    @staticmethod
    def _format_number(number: int) -> str:
        """숫자 천단위 구분자"""
        return f"{number:,}"
    
    @staticmethod
    def _format_percentage(ratio: float) -> str:
        """백분율 포맷팅"""
        return f"{ratio:.1f}%"
    
    def _get_competitor_data(self) -> List[Dict]:
        """경쟁사 SSL 현황 데이터 (하드코딩된 샘플)"""
        return [
            {'name': 'Company A', 'ssl_grade': 'A+', 'security_score': 95, 'grade_class': 'aplus', 'status': 'excellent', 'status_text': '우수'},
            {'name': 'Company B', 'ssl_grade': 'A', 'security_score': 88, 'grade_class': 'a', 'status': 'good', 'status_text': '양호'},
            {'name': 'Company C', 'ssl_grade': 'B', 'security_score': 75, 'grade_class': 'b', 'status': 'fair', 'status_text': '보통'}
        ]
```

### 3. FastAPI 백엔드

```python
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import asyncio
import os

app = FastAPI(title="SecureCheck Pro API", version="1.0.0")

class AnalysisRequest(BaseModel):
    url: HttpUrl
    include_competitor_analysis: bool = True
    report_format: str = "pdf"  # pdf, json

class AnalysisResponse(BaseModel):
    analysis_id: str
    status: str
    estimated_completion_time: int

# 전역 인스턴스
analyzer = SecurityAnalyzer()
report_generator = ReportGenerator()

@app.post("/api/v1/analyze", response_model=AnalysisResponse)
async def analyze_website(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """웹사이트 보안 분석 시작"""
    
    domain = request.url.host
    analysis_id = f"analysis_{domain}_{int(datetime.now().timestamp())}"
    
    # 백그라운드에서 분석 실행
    background_tasks.add_task(perform_analysis, analysis_id, domain, request.report_format)
    
    return AnalysisResponse(
        analysis_id=analysis_id,
        status="started",
        estimated_completion_time=60  # 60초 예상
    )

async def perform_analysis(analysis_id: str, domain: str, report_format: str):
    """실제 분석 수행 (백그라운드 작업)"""
    try:
        # Step 1: 도메인 분석
        result = await analyzer.analyze_website(domain)
        
        # Step 2: 보고서 생성
        if report_format == "pdf":
            report_path = report_generator.generate_report(result)
            
            # 분석 결과 저장 (데이터베이스에 저장)
            await save_analysis_result(analysis_id, result, report_path)
        
    except Exception as e:
        # 에러 로깅 및 실패 상태 업데이트
        await update_analysis_status(analysis_id, "failed", str(e))

@app.get("/api/v1/analysis/{analysis_id}/status")
async def get_analysis_status(analysis_id: str):
    """분석 진행 상태 확인"""
    # 데이터베이스에서 상태 조회
    status_info = await get_analysis_status_from_db(analysis_id)
    
    if not status_info:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return status_info

@app.get("/api/v1/analysis/{analysis_id}/report")
async def download_report(analysis_id: str):
    """보고서 다운로드"""
    report_info = await get_report_info_from_db(analysis_id)
    
    if not report_info or not os.path.exists(report_info['file_path']):
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        path=report_info['file_path'],
        filename=f"{report_info['domain']}_security_report.pdf",
        media_type='application/pdf'
    )

@app.get("/api/v1/analysis/{analysis_id}/json")
async def get_analysis_json(analysis_id: str):
    """분석 결과 JSON 형태로 반환"""
    result = await get_analysis_result_from_db(analysis_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    
    return result
```

---

## 📱 프론트엔드 구현 (React/Next.js)

### 4. 메인 분석 페이지 구현

```typescript
// pages/analyze.tsx
import React, { useState } from 'react';
import { URLInput } from '../components/URLInput';
import { ProgressTracker } from '../components/ProgressTracker';
import { ResultSummary } from '../components/ResultSummary';
import { AnalysisService } from '../services/AnalysisService';

interface AnalysisState {
  phase: 'input' | 'analyzing' | 'completed' | 'error';
  analysisId?: string;
  result?: AnalysisResult;
  error?: string;
}

export default function AnalyzePage() {
  const [state, setState] = useState<AnalysisState>({ phase: 'input' });
  const [steps, setSteps] = useState<AnalysisStep[]>([
    { name: '기본 연결 테스트', description: 'HTTPS 서비스 확인', duration: 10, status: 'pending' },
    { name: 'SSL 인증서 분석', description: '인증서 정보 추출 및 검증', duration: 15, status: 'pending' },
    { name: '보안 헤더 검사', description: 'HSTS, CSP 등 보안 헤더 분석', duration: 10, status: 'pending' },
    { name: '성능 측정', description: '페이지 로딩 속도 및 최적화 분석', duration: 10, status: 'pending' },
    { name: '보고서 생성', description: '케이스별 맞춤 보고서 생성', duration: 5, status: 'pending' }
  ]);

  const handleAnalyze = async (url: string) => {
    setState({ phase: 'analyzing' });
    
    try {
      // 분석 시작
      const response = await AnalysisService.startAnalysis(url);
      setState(prev => ({ ...prev, analysisId: response.analysis_id }));
      
      // 진행상황 추적
      await trackProgress(response.analysis_id);
      
    } catch (error) {
      setState({ 
        phase: 'error', 
        error: error instanceof Error ? error.message : 'Unknown error' 
      });
    }
  };

  const trackProgress = async (analysisId: string) => {
    let currentStep = 0;
    const interval = setInterval(async () => {
      try {
        const status = await AnalysisService.getAnalysisStatus(analysisId);
        
        if (status.status === 'completed') {
          clearInterval(interval);
          const result = await AnalysisService.getAnalysisResult(analysisId);
          setState({ phase: 'completed', result });
          
          // 모든 스텝 완료 표시
          setSteps(prev => prev.map(step => ({ ...step, status: 'completed' })));
        } else if (status.status === 'failed') {
          clearInterval(interval);
          setState({ phase: 'error', error: status.error });
        } else {
          // 진행 중 - 현재 스텝 업데이트
          if (currentStep < steps.length) {
            setSteps(prev => prev.map((step, index) => ({
              ...step,
              status: index < currentStep ? 'completed' : 
                      index === currentStep ? 'running' : 'pending'
            })));
            currentStep++;
          }
        }
      } catch (error) {
        clearInterval(interval);
        setState({ phase: 'error', error: 'Analysis failed' });
      }
    }, 3000); // 3초마다 상태 확인
  };

  return (
    <div className="analyze-page">
      <div className="container">
        <h1>웹사이트 보안 분석</h1>
        
        {state.phase === 'input' && (
          <URLInput onAnalyze={handleAnalyze} isLoading={false} />
        )}
        
        {state.phase === 'analyzing' && (
          <ProgressTracker steps={steps} />
        )}
        
        {state.phase === 'completed' && state.result && (
          <ResultSummary result={state.result} />
        )}
        
        {state.phase === 'error' && (
          <div className="error-container">
            <h2>분석 중 오류가 발생했습니다</h2>
            <p>{state.error}</p>
            <button onClick={() => setState({ phase: 'input' })}>
              다시 시도
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
```

### 5. 분석 서비스 클래스

```typescript
// services/AnalysisService.ts
class AnalysisService {
  private static baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  static async startAnalysis(url: string): Promise<AnalysisResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url: url,
        report_format: 'pdf'
      })
    });

    if (!response.ok) {
      throw new Error('분석을 시작할 수 없습니다');
    }

    return response.json();
  }

  static async getAnalysisStatus(analysisId: string): Promise<AnalysisStatusResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/analysis/${analysisId}/status`);
    
    if (!response.ok) {
      throw new Error('분석 상태를 확인할 수 없습니다');
    }

    return response.json();
  }

  static async getAnalysisResult(analysisId: string): Promise<AnalysisResult> {
    const response = await fetch(`${this.baseUrl}/api/v1/analysis/${analysisId}/json`);
    
    if (!response.ok) {
      throw new Error('분석 결과를 가져올 수 없습니다');
    }

    return response.json();
  }

  static getReportDownloadUrl(analysisId: string): string {
    return `${this.baseUrl}/api/v1/analysis/${analysisId}/report`;
  }
}

export { AnalysisService };
```

---

## 🗄️ 데이터베이스 스키마

### PostgreSQL 테이블 설계

```sql
-- 사용자 테이블
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    subscription_plan VARCHAR(50) DEFAULT 'free',
    analysis_count INTEGER DEFAULT 0,
    monthly_limit INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 웹사이트 분석 요청 테이블
CREATE TABLE analysis_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id VARCHAR(100) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id),
    domain VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, analyzing, completed, failed
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT,
    estimated_completion INTEGER DEFAULT 60
);

-- SSL 분석 결과 테이블
CREATE TABLE ssl_analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id VARCHAR(100) REFERENCES analysis_requests(analysis_id),
    case_type VARCHAR(50) NOT NULL, -- no_ssl, self_signed, expired, domain_mismatch, valid
    security_grade VARCHAR(5) NOT NULL, -- A+, A, B, C, D, F
    security_score INTEGER NOT NULL,
    
    -- SSL 세부 정보 (JSONB)
    ssl_details JSONB DEFAULT '{}',
    server_issues JSONB DEFAULT '{}',
    business_impact JSONB DEFAULT '{}',
    
    -- 인증서 정보
    cert_subject VARCHAR(500),
    cert_issuer VARCHAR(500),
    cert_valid_from TIMESTAMP,
    cert_valid_to TIMESTAMP,
    is_self_signed BOOLEAN DEFAULT FALSE,
    is_expired BOOLEAN DEFAULT FALSE,
    
    analyzed_at TIMESTAMP DEFAULT NOW()
);

-- 보고서 파일 테이블
CREATE TABLE analysis_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id VARCHAR(100) REFERENCES analysis_requests(analysis_id),
    report_type VARCHAR(20) DEFAULT 'pdf', -- pdf, json
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    template_used VARCHAR(100),
    generated_at TIMESTAMP DEFAULT NOW()
);

-- 권장사항 테이블 (정규화)
CREATE TABLE analysis_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id VARCHAR(100) REFERENCES analysis_requests(analysis_id),
    priority VARCHAR(20) NOT NULL, -- critical, high, medium, low
    title VARCHAR(200) NOT NULL,
    description TEXT,
    implementation_time VARCHAR(50),
    cost INTEGER DEFAULT 0,
    expected_impact JSONB DEFAULT '{}',
    commands TEXT[],
    sort_order INTEGER DEFAULT 0
);

-- 경쟁사 데이터 테이블 (하드코딩된 데이터용)
CREATE TABLE competitor_ssl_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(100) NOT NULL,
    domain VARCHAR(255),
    industry VARCHAR(100),
    ssl_grade VARCHAR(5),
    security_score INTEGER,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX idx_analysis_requests_domain ON analysis_requests(domain);
CREATE INDEX idx_analysis_requests_status ON analysis_requests(status);
CREATE INDEX idx_ssl_analysis_case_type ON ssl_analysis_results(case_type);
CREATE INDEX idx_analysis_reports_analysis_id ON analysis_reports(analysis_id);

-- 샘플 경쟁사 데이터 삽입
INSERT INTO competitor_ssl_data (company_name, domain, industry, ssl_grade, security_score) VALUES
('Company A', 'company-a.com', 'manufacturing', 'A+', 95),
('Company B', 'company-b.co.kr', 'manufacturing', 'A', 88),
('Company C', 'company-c.com', 'manufacturing', 'B', 75),
('Global Leader', 'global-leader.com', 'manufacturing', 'A+', 98);
```

---

## 🔄 고정 플로우 분석 로직 상세

### 분석 단계별 세부 구현

```python
# analysis_flow.py
from enum import Enum
from typing import Dict, List, Tuple
import asyncio

class AnalysisStep(Enum):
    CONNECTION_TEST = "connection_test"
    SSL_CERTIFICATE = "ssl_certificate" 
    SECURITY_HEADERS = "security_headers"
    PERFORMANCE = "performance"
    REPORT_GENERATION = "report_generation"

class FixedFlowAnalyzer:
    """고정 플로우 기반 보안 분석기"""
    
    def __init__(self):
        self.step_timeouts = {
            AnalysisStep.CONNECTION_TEST: 10,
            AnalysisStep.SSL_CERTIFICATE: 15,
            AnalysisStep.SECURITY_HEADERS: 10,
            AnalysisStep.PERFORMANCE: 10,
            AnalysisStep.REPORT_GENERATION: 5
        }
    
    async def analyze_with_progress(self, domain: str, progress_callback=None) -> SecurityAnalysisResult:
        """진행상황을 추적하면서 분석 수행"""
        results = {}
        
        for step in AnalysisStep:
            if progress_callback:
                await progress_callback(step, 'started')
            
            try:
                step_result = await self._execute_step(step, domain, results)
                results[step] = step_result
                
                if progress_callback:
                    await progress_callback(step, 'completed', step_result)
                    
            except Exception as e:
                if progress_callback:
                    await progress_callback(step, 'failed', {'error': str(e)})
                raise
        
        # 최종 결과 종합
        return self._compile_final_result(domain, results)
    
    async def _execute_step(self, step: AnalysisStep, domain: str, previous_results: Dict) -> Dict:
        """각 단계별 실행 로직"""
        timeout = self.step_timeouts[step]
        
        if step == AnalysisStep.CONNECTION_TEST:
            return await asyncio.wait_for(
                self._test_connection(domain), 
                timeout=timeout
            )
        elif step == AnalysisStep.SSL_CERTIFICATE:
            return await asyncio.wait_for(
                self._analyze_ssl_certificate(domain, previous_results[AnalysisStep.CONNECTION_TEST]),
                timeout=timeout
            )
        elif step == AnalysisStep.SECURITY_HEADERS:
            return await asyncio.wait_for(
                self._check_security_headers(domain),
                timeout=timeout
            )
        elif step == AnalysisStep.PERFORMANCE:
            return await asyncio.wait_for(
                self._measure_performance(domain),
                timeout=timeout
            )
        elif step == AnalysisStep.REPORT_GENERATION:
            return await asyncio.wait_for(
                self._prepare_report_data(domain, previous_results),
                timeout=timeout
            )
    
    async def _test_connection(self, domain: str) -> Dict:
        """Step 1: 기본 연결 테스트"""
        return {
            'http_available': await self._check_http_port(domain, 80),
            'https_available': await self._check_http_port(domain, 443),
            'ping_response_time': await self._ping_domain(domain),
            'dns_resolution': await self._resolve_dns(domain)
        }
    
    async def _analyze_ssl_certificate(self, domain: str, connection_info: Dict) -> Dict:
        """Step 2: SSL 인증서 분석"""
        if not connection_info['https_available']:
            return {
                'status': 'no_ssl',
                'case_type': SSLCaseType.NO_SSL,
                'details': 'HTTPS port not available'
            }
        
        cert_info = await self._extract_certificate_info(domain)
        case_type = self._classify_ssl_case(domain, cert_info)
        
        return {
            'status': 'has_ssl',
            'case_type': case_type,
            'certificate_info': cert_info,
            'ssl_labs_grade': await self._get_ssl_labs_grade(domain),
            'tls_versions': await self._check_tls_versions(domain),
            'cipher_suites': await self._analyze_cipher_suites(domain)
        }
    
    async def _check_security_headers(self, domain: str) -> Dict:
        """Step 3: 보안 헤더 검사"""
        headers_to_check = [
            'Strict-Transport-Security',
            'X-Frame-Options',
            'X-Content-Type-Options',
            'X-XSS-Protection',
            'Content-Security-Policy',
            'Referrer-Policy'
        ]
        
        results = {}
        try:
            response = requests.get(f'https://{domain}', timeout=10, verify=False)
            for header in headers_to_check:
                results[header] = {
                    'present': header in response.headers,
                    'value': response.headers.get(header, ''),
                    'score': self._score_security_header(header, response.headers.get(header, ''))
                }
        except:
            # HTTPS 실패시 HTTP로 재시도
            try:
                response = requests.get(f'http://{domain}', timeout=10)
                for header in headers_to_check:
                    results[header] = {
                        'present': header in response.headers,
                        'value': response.headers.get(header, ''),
                        'score': 0  # HTTP에서는 보안 헤더 점수 0점
                    }
            except:
                results = {header: {'present': False, 'value': '', 'score': 0} for header in headers_to_check}
        
        return {
            'headers': results,
            'total_score': sum(h['score'] for h in results.values()),
            'max_score': len(headers_to_check) * 10
        }
    
    async def _measure_performance(self, domain: str) -> Dict:
        """Step 4: 성능 측정"""
        performance_data = {}
        
        # HTTP/HTTPS 응답 시간 측정
        for protocol in ['http', 'https']:
            try:
                start_time = time.time()
                response = requests.get(f'{protocol}://{domain}', timeout=10, verify=False)
                end_time = time.time()
                
                performance_data[f'{protocol}_response_time'] = (end_time - start_time) * 1000  # ms
                performance_data[f'{protocol}_status_code'] = response.status_code
                performance_data[f'{protocol}_content_length'] = len(response.content)
            except Exception as e:
                performance_data[f'{protocol}_error'] = str(e)
        
        # HTTP/2 지원 여부 확인
        performance_data['http2_support'] = await self._check_http2_support(domain)
        
        # 압축 지원 여부
        performance_data['compression_support'] = await self._check_compression_support(domain)
        
        return performance_data
    
    def _compile_final_result(self, domain: str, step_results: Dict) -> SecurityAnalysisResult:
        """모든 단계 결과를 종합하여 최종 결과 생성"""
        ssl_result = step_results[AnalysisStep.SSL_CERTIFICATE]
        headers_result = step_results[AnalysisStep.SECURITY_HEADERS] 
        performance_result = step_results[AnalysisStep.PERFORMANCE]
        
        # 케이스 타입 결정
        case_type = ssl_result.get('case_type', SSLCaseType.NO_SSL)
        
        # 보안 점수 계산 (고정 공식)
        security_score = self._calculate_security_score(ssl_result, headers_result)
        security_grade = self._score_to_grade(security_score)
        
        # 비즈니스 영향 계산
        business_impact = self._calculate_business_impact(case_type, security_score, domain)
        
        # 권장사항 생성
        recommendations = self._generate_recommendations(case_type, ssl_result, headers_result)
        
        return SecurityAnalysisResult(
            domain=domain,
            case_type=case_type,
            security_grade=security_grade,
            security_score=security_score,
            ssl_details=ssl_result,
            server_issues=performance_result,
            business_impact=business_impact,
            recommendations=recommendations,
            analysis_timestamp=datetime.utcnow()
        )
    
    def _calculate_security_score(self, ssl_result: Dict, headers_result: Dict) -> int:
        """보안 점수 계산 (고정 공식)"""
        score = 0
        
        # SSL 점수 (40점 만점)
        if ssl_result['status'] == 'no_ssl':
            ssl_score = 0
        elif ssl_result['case_type'] == SSLCaseType.SELF_SIGNED:
            ssl_score = 10
        elif ssl_result['case_type'] == SSLCaseType.EXPIRED:
            ssl_score = 5
        elif ssl_result['case_type'] == SSLCaseType.DOMAIN_MISMATCH:
            ssl_score = 15
        else:  # VALID
            # SSL Labs 등급에 따른 점수
            grade_scores = {'A+': 40, 'A': 35, 'B': 30, 'C': 20, 'D': 10, 'F': 0}
            ssl_score = grade_scores.get(ssl_result.get('ssl_labs_grade', 'F'), 0)
        
        score += ssl_score
        
        # 보안 헤더 점수 (20점 만점)
        headers_score = min(20, headers_result['total_score'] * 20 // headers_result['max_score'])
        score += headers_score
        
        # 프로토콜 지원 점수 (15점 만점)
        if ssl_result.get('tls_versions'):
            tls_score = 0
            if 'TLSv1.3' in ssl_result['tls_versions']:
                tls_score = 15
            elif 'TLSv1.2' in ssl_result['tls_versions']:
                tls_score = 10
            else:
                tls_score = 5
        else:
            tls_score = 0
        
        score += tls_score
        
        # 암호화 강도 점수 (25점 만점)
        cipher_score = self._calculate_cipher_score(ssl_result.get('cipher_suites', []))
        score += cipher_score
        
        return min(100, score)
    
    def _score_to_grade(self, score: int) -> str:
        """점수를 등급으로 변환"""
        if score >= 95:
            return 'A+'
        elif score >= 85:
            return 'A'
        elif score >= 75:
            return 'B'
        elif score >= 65:
            return 'C'
        elif score >= 50:
            return 'D'
        else:
            return 'F'
```

---

## 🎨 CSS 스타일 시트 (보고서용)

### report_styles.css
```css
/* 보고서 기본 스타일 */
@page {
    size: A4;
    margin: 2cm;
}

body {
    font-family: 'Noto Sans KR', Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    margin: 0;
    padding: 0;
}

/* 헤더 스타일 */
.report-header {
    border-bottom: 3px solid #007bff;
    margin-bottom: 30px;
    padding-bottom: 20px;
}

.report-header h1 {
    color: #007bff;
    font-size: 28px;
    margin-bottom: 10px;
}

.report-meta {
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
}

.report-meta p {
    margin: 5px 0;
    font-size: 14px;
}

/* 등급 표시 */
.grade {
    font-weight: bold;
    padding: 5px 10px;
    border-radius: 4px;
    color: white;
}

.grade-aplus, .grade-a { background-color: #28a745; }
.grade-b { background-color: #ffc107; color: #000; }
.grade-c { background-color: #fd7e14; }
.grade-d, .grade-f { background-color: #dc3545; }

/* 섹션 스타일 */
section {
    margin-bottom: 40px;
    page-break-inside: avoid;
}

section h2 {
    color: #007bff;
    font-size: 22px;
    margin-bottom: 20px;
    border-left: 4px solid #007bff;
    padding-left: 15px;
}

section h3 {
    color: #495057;
    font-size: 18px;
    margin-bottom: 15px;
}

/* 경고 박스 */
.critical-alert {
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
}

.critical-alert h3 {
    color: #721c24;
    margin-top: 0;
}

.warning-alert {
    background-color: #fff3cd;
    border: 1px solid #ffeaa7;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
}

.warning-alert h3 {
    color: #856404;
    margin-top: 0;
}

/* 메트릭 표시 */
.impact-metrics {
    display: flex;
    justify-content: space-around;
    margin: 20px 0;
}

.metric {
    text-align: center;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
    min-width: 120px;
}

.metric .number {
    display: block;
    font-size: 24px;
    font-weight: bold;
    color: #dc3545;
}

.metric .label {
    font-size: 12px;
    color: #6c757d;
    margin-top: 5px;
}

/* 분석 그리드 */
.analysis-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin: 20px 0;
}

.analysis-item {
    padding: 20px;
    border-radius: 8px;
    border-left: 4px solid #6c757d;
}

.analysis-item.failed {
    background-color: #f8d7da;
    border-left-color: #dc3545;
}

.analysis-item.warning {
    background-color: #fff3cd;
    border-left-color: #ffc107;
}

.analysis-item.success {
    background-color: #d4edda;
    border-left-color: #28a745;
}

.analysis-item.info {
    background-color: #d1ecf1;
    border-left-color: #17a2b8;
}

.analysis-item h3 {
    margin-top: 0;
    margin-bottom: 10px;
}

.analysis-item .status {
    font-weight: bold;
    margin-bottom: 10px;
}

/* 점수 분석 */
.security-score-breakdown {
    background-color: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    margin: 20px 0;
}

.score-item {
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid #dee2e6;
}

.score-item:last-child {
    border-bottom: none;
}

.score-item.total-score {
    font-weight: bold;
    font-size: 16px;
    border-top: 2px solid #007bff;
    margin-top: 10px;
    padding-top: 15px;
}

/* 테이블 스타일 */
.comparison-table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 14px;
}

.comparison-table th,
.comparison-table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #dee2e6;
}

.comparison-table th {
    background-color: #007bff;
    color: white;
    font-weight: bold;
}

.comparison-table tr:hover {
    background-color: #f8f9fa;
}

.comparison-table tr.current-site {
    background-color: #fff3cd;
    font-weight: bold;
}

.status-excellent { color: #28a745; }
.status-good { color: #17a2b8; }
.status-fair { color: #ffc107; }
.status-poor { color: #fd7e14; }
.status-critical { color: #dc3545; }

/* 해결방안 스타일 */
.solution-timeline {
    margin: 30px 0;
}

.phase {
    margin-bottom: 30px;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    overflow: hidden;
}

.phase-header {
    padding: 15px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
}

.phase-urgent .phase-header {
    background-color: #dc3545;
    color: white;
}

.phase-important .phase-header {
    background-color: #ffc107;
    color: #000;
}

.phase-recommended .phase-header {
    background-color: #17a2b8;
    color: white;
}

.phase-header h4 {
    margin: 0;
    font-size: 16px;
}

.duration, .cost {
    font-size: 12px;
    padding: 4px 8px;
    background-color: rgba(255,255,255,0.2);
    border-radius: 4px;
    margin-left: 10px;
}

.phase-content {
    padding: 20px;
}

.phase-content h5 {
    color: #495057;
    margin-top: 0;
    margin-bottom: 15px;
}

/* 코드 블록 */
.code-block {
    margin: 15px 0;
}

.code-block h6 {
    color: #495057;
    font-size: 14px;
    margin-bottom: 8px;
}

.code-block pre {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 4px;
    padding: 15px;
    overflow-x: auto;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.4;
}

.code-block code {
    color: #e83e8c;
}

/* 예상 결과 */
.expected-result {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    border-radius: 4px;
    padding: 15px;
    margin-top: 15px;
}

.expected-result h6 {
    color: #155724;
    margin-top: 0;
    margin-bottom: 10px;
}

.expected-result ul {
    margin: 0;
    padding-left: 20px;
}

.expected-result li {
    margin-bottom: 5px;
}

/* ROI 분석 */
.roi-analysis {
    background-color: #e7f3ff;
    border: 1px solid #b8daff;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
}

.roi-metrics {
    display: flex;
    justify-content: space-around;
    margin-top: 15px;
}

.roi-item {
    text-align: center;
}

.roi-item .label {
    font-size: 14px;
    color: #495057;
    margin-bottom: 5px;
}

.roi-item .value {
    font-size: 18px;
    font-weight: bold;
    color: #007bff;
}

.roi-item .value.highlight {
    color: #28a745;
    font-size: 20px;
}

/* 계산 단계 */
.calculation-steps {
    background-color: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    margin: 15px 0;
}

.step {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid #dee2e6;
}

.step:last-child {
    border-bottom: none;
    font-weight: bold;
    font-size: 16px;
}

.step .label {
    color: #495057;
}

.step .value.highlight {
    color: #dc3545;
    font-weight: bold;
}

/* 인쇄용 최적화 */
@media print {
    .no-print { display: none; }
    
    .page-break {
        page-break-before: always;
    }
    
    .avoid-break {
        page-break-inside: avoid;
    }
    
    /* 색상을 회색조로 변경 (인쇄 비용 절약) */
    .critical-alert {
        background-color: #f5f5f5;
        border-color: #ddd;
    }
    
    .grade {
        background-color: #666 !important;
        color: white !important;
    }
}

/* 반응형 디자인 (웹 미리보기용) */
@media screen and (max-width: 768px) {
    .impact-metrics {
        flex-direction: column;
        gap: 10px;
    }
    
    .analysis-grid {
        grid-template-columns: 1fr;
    }
    
    .phase-header {
        flex-direction: column;
        align-items: flex-start;
    }
    
    .duration, .cost {
        margin-left: 0;
        margin-top: 5px;
    }
    
    .roi-metrics {
        flex-direction: column;
        gap: 15px;
    }
}
```

---

## 📁 프로젝트 구조

### 디렉토리 구조
```
website-security-analyzer/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI 앱 진입점
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── analysis.py            # 분석 결과 모델
│   │   │   ├── ssl.py                 # SSL 관련 모델
│   │   │   └── user.py                # 사용자 모델
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── analyzer.py            # 메인 분석 서비스
│   │   │   ├── ssl_analyzer.py        # SSL 분석 전용
│   │   │   ├── report_generator.py    # 보고서 생성
│   │   │   └── database.py            # DB 연결/쿼리
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── analysis.py            # 분석 API 엔드포인트
│   │   │   ├── reports.py             # 보고서 API
│   │   │   └── users.py               # 사용자 API
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py              # 설정 관리
│   │   │   ├── security.py            # 보안 유틸리티
│   │   │   └── database.py            # DB 설정
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── ssl_utils.py           # SSL 유틸리티
│   │       ├── network_utils.py       # 네트워크 유틸리티
│   │       └── report_utils.py        # 보고서 유틸리티
│   ├── templates/
│   │   ├── base_template.html         # 기본 템플릿
│   │   ├── no_ssl_template.html       # SSL 부재 템플릿
│   │   ├── self_signed_template.html  # 자체서명 템플릿
│   │   ├── expired_cert_template.html # 만료 템플릿
│   │   ├── domain_mismatch_template.html # 도메인불일치 템플릿
│   │   ├── valid_ssl_template.html    # 정상 SSL 템플릿
│   │   └── report_styles.css          # 보고서 CSS
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_analyzer.py
│   │   ├── test_ssl.py
│   │   └── test_reports.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── URLInput.tsx           # URL 입력 컴포넌트
│   │   │   ├── ProgressTracker.tsx    # 진행상황 추적
│   │   │   ├── ResultSummary.tsx      # 결과 요약
│   │   │   └── SecurityGrade.tsx      # 보안 등급 표시
│   │   ├── pages/
│   │   │   ├── index.tsx              # 메인 페이지
│   │   │   ├── analyze.tsx            # 분석 페이지
│   │   │   └── result/[id].tsx        # 결과 상세 페이지
│   │   ├── services/
│   │   │   ├── AnalysisService.ts     # 분석 API 서비스
│   │   │   └── ApiClient.ts           # API 클라이언트
│   │   ├── types/
│   │   │   ├── analysis.ts            # 분석 관련 타입
│   │   │   └── ssl.ts                 # SSL 관련 타입
│   │   ├── hooks/
│   │   │   ├── useAnalysis.ts         # 분석 훅
│   │   │   └── usePolling.ts          # 폴링 훅
│   │   └── styles/
│   │       ├── globals.css
│   │       └── components.css
│   ├── public/
│   │   ├── images/
│   │   └── icons/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   └── Dockerfile
├── database/
│   ├── migrations/
│   │   ├── 001_initial_schema.sql
│   │   ├── 002_add_indexes.sql
│   │   └── 003_sample_data.sql
│   └── schema.sql
├── reports/                           # 생성된 보고서 저장
├── docs/
│   ├── API.md                         # API 문서
│   ├── DEPLOYMENT.md                  # 배포 가이드
│   └── DEVELOPMENT.md                 # 개발 가이드
├── docker-compose.yml                 # 전체 스택 구성
├── .env.example
├── .gitignore
└── README.md
```

---

## 🔧 개발 환경 설정

### 1. Backend 설정 (Python/FastAPI)

#### requirements.txt
```txt
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0

# Database & Cache
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1
redis==5.0.1
celery==5.3.4

# Browser Automation (핵심)
playwright==1.40.0

# Template & PDF
jinja2==3.1.2
weasyprint==60.2

# Network Analysis
requests==2.31.0
cryptography==41.0.8
python-multipart==0.0.6

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-playwright==0.4.3
httpx==0.25.2

# Security & Monitoring
slowapi==0.1.9  # Rate limiting
python-jose==3.3.0  # JWT tokens
```

#### main.py (FastAPI 앱)
```python
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.api import analysis, reports, users
from app.core.config import settings
from app.core.database import engine
from app.models import analysis as analysis_models

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작시 실행
    print("🚀 SecureCheck Pro API Starting...")
    
    # 데이터베이스 테이블 생성
    analysis_models.Base.metadata.create_all(bind=engine)
    
    yield
    
    # 종료시 실행
    print("🛑 SecureCheck Pro API Shutting down...")

app = FastAPI(
    title="SecureCheck Pro API",
    description="웹사이트 보안 분석 및 보고서 생성 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 (생성된 보고서)
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

# API 라우터 등록
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])

@app.get("/")
async def root():
    return {
        "message": "SecureCheck Pro API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2. Frontend 설정 (Next.js/TypeScript)

#### package.json
```json
{
  "name": "securecheck-pro-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "next": "14.0.3",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "@types/node": "20.9.0",
    "@types/react": "18.2.37",
    "@types/react-dom": "18.2.15",
    "typescript": "5.2.2",
    "tailwindcss": "3.3.5",
    "autoprefixer": "10.4.16",
    "postcss": "8.4.31",
    "lucide-react": "0.293.0",
    "framer-motion": "10.16.5",
    "recharts": "2.8.0"
  },
  "devDependencies": {
    "eslint": "8.54.0",
    "eslint-config-next": "14.0.3",
    "@typescript-eslint/eslint-plugin": "6.12.0",
    "@typescript-eslint/parser": "6.12.0"
  }
}
```

#### next.config.js
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
    ];
  },
  images: {
    domains: ['localhost'],
  },
};

module.exports = nextConfig;
```

### 3. Docker 설정

#### docker-compose.yml (전체 스택)
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: securecheck-postgres
    environment:
      POSTGRES_DB: securecheck_pro
      POSTGRES_USER: securecheck_user
      POSTGRES_PASSWORD: securecheck_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
      - ./database/migrations/003_sample_data.sql:/docker-entrypoint-initdb.d/02-sample.sql
    networks:
      - securecheck-network

  redis:
    image: redis:7-alpine
    container_name: securecheck-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - securecheck-network

  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    container_name: securecheck-backend
    environment:
      - DATABASE_URL=postgresql://securecheck_user:securecheck_password@postgres:5432/securecheck_pro
      - REDIS_URL=redis://redis:6379
      - ENVIRONMENT=development
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app
      - ./reports:/app/reports
    networks:
      - securecheck-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: securecheck-frontend
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules
    networks:
      - securecheck-network

  nginx:
    image: nginx:alpine
    container_name: securecheck-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
    networks:
      - securecheck-network

volumes:
  postgres_data:
  redis_data:

networks:
  securecheck-network:
    driver: bridge
```

---

## 🚀 배포 및 운영

### 개발 환경 실행
```bash
# 1. 프로젝트 클론
git clone <repository-url>
cd website-security-analyzer

# 2. 환경변수 설정
cp .env.example .env
# .env 파일 편집

# 3. Docker Compose로 전체 스택 실행
docker-compose up -d

# 4. 데이터베이스 마이그레이션 (필요시)
docker-compose exec backend alembic upgrade head

# 5. 서비스 확인
curl http://localhost:8000/health  # Backend 헬스체크
curl http://localhost:3000         # Frontend 접속
```

### 프로덕션 배포
```bash
# 1. 프로덕션 환경변수 설정
export ENVIRONMENT=production
export DATABASE_URL=postgresql://user:pass@prod-db:5432/db
export REDIS_URL=redis://prod-redis:6379

# 2. Docker 이미지 빌드
docker-compose -f docker-compose.prod.yml build

# 3. 프로덕션 서비스 시작
docker-compose -f docker-compose.prod.yml up -d

# 4. SSL 인증서 설정 (Let's Encrypt)
docker-compose exec nginx certbot --nginx -d yourdomain.com

# 5. 로그 모니터링
docker-compose logs -f backend
```

---

## 📊 성능 최적화 및 모니터링

### 캐싱 전략
```python
# Redis 캐싱 구현
import redis
import json
from typing import Optional

class CacheService:
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
    
    async def get_analysis_cache(self, domain: str) -> Optional[dict]:
        """도메인별 분석 결과 캐시 조회"""
        cache_key = f"analysis:{domain}"
        cached_data = self.redis_client.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        return None
    
    async def set_analysis_cache(self, domain: str, analysis_result: dict, ttl: int = 3600):
        """분석 결과 캐시 저장 (1시간 TTL)"""
        cache_key = f"analysis:{domain}"
        self.redis_client.setex(
            cache_key, 
            ttl, 
            json.dumps(analysis_result, default=str)
        )
```

### 모니터링 및 로깅
```python
import logging
import time
from functools import wraps

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/securecheck/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("securecheck")

def monitor_performance(func):
    """성능 모니터링 데코레이터"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.info(f"{func.__name__} completed in {execution_time:.2f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {str(e)}")
            raise
    return wrapper

# 사용 예시
@monitor_performance
async def analyze_ssl_certificate(self, domain: str):
    # SSL 분석 로직
    pass
```

---

## ✅ 테스트 전략

### 단위 테스트
```python
# tests/test_ssl_analyzer.py
import pytest
from unittest.mock import Mock, patch
from app.services.ssl_analyzer import SSLAnalyzer, SSLCaseType

class TestSSLAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return SSLAnalyzer()
    
    @pytest.mark.asyncio
    async def test_detect_no_ssl(self, analyzer):
        """SSL 부재 케이스 테스트"""
        with patch('socket.socket') as mock_socket:
            mock_socket.return_value.connect_ex.return_value = 1  # 연결 실패
            
            result = await analyzer._check_ssl_availability('no-ssl-domain.com')
            assert result is False
    
    @pytest.mark.asyncio 
    async def test_detect_self_signed(self, analyzer):
        """자체 서명 인증서 테스트"""
        mock_cert = {
            'subject': [('CN', 'test.com')],
            'issuer': [('CN', 'test.com')],  # subject와 동일
            'notBefore': 'Jan 1 00:00:00 2023 GMT',
            'notAfter': 'Jan 1 00:00:00 2124 GMT'
        }
        
        with patch.object(analyzer, '_extract_certificate_info', return_value=mock_cert):
            case_type = analyzer._classify_ssl_case('test.com', mock_cert)
            assert case_type == SSLCaseType.SELF_SIGNED
    
    def test_security_score_calculation(self, analyzer):
        """보안 점수 계산 테스트"""
        ssl_result = {
            'status': 'no_ssl',
            'case_type': SSLCaseType.NO_SSL
        }
        headers_result = {
            'total_score': 0,
            'max_score': 60
        }
        
        score = analyzer._calculate_security_score(ssl_result, headers_result)
        assert score == 0  # SSL 없으면 0점
```

### 통합 테스트
```python
# tests/test_analysis_flow.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestAnalysisFlow:
    def test_complete_analysis_flow(self):
        """전체 분석 플로우 테스트"""
        # 1. 분석 시작
        response = client.post("/api/v1/analyze", json={
            "url": "https://example.com",
            "report_format": "pdf"
        })
        assert response.status_code == 200
        analysis_id = response.json()["analysis_id"]
        
        # 2. 상태 확인 (폴링)
        import time
        max_wait = 60  # 최대 60초 대기
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_response = client.get(f"/api/v1/analysis/{analysis_id}/status")
            status = status_response.json()["status"]
            
            if status == "completed":
                break
            elif status == "failed":
                pytest.fail("Analysis failed")
            
            time.sleep(2)
        
        # 3. 결과 확인
        result_response = client.get(f"/api/v1/analysis/{analysis_id}/json")
        assert result_response.status_code == 200
        
        result = result_response.json()
        assert "domain" in result
        assert "security_grade" in result
        assert "case_type" in result
```

### 성능 테스트
```python
# tests/test_performance.py
import pytest
import asyncio
import time
from app.services.analyzer import SecurityAnalyzer

class TestPerformance:
    @pytest.mark.asyncio
    async def test_analysis_performance(self):
        """분석 성능 테스트 - 60초 이내 완료"""
        analyzer = SecurityAnalyzer()
        
        start_time = time.time()
        result = await analyzer.analyze_website("google.com")
        execution_time = time.time() - start_time
        
        assert execution_time < 60, f"Analysis took {execution_time:.2f}s, should be under 60s"
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis(self):
        """동시 분석 성능 테스트"""
        analyzer = SecurityAnalyzer()
        domains = ["google.com", "github.com", "stackoverflow.com"]
        
        start_time = time.time()
        tasks = [analyzer.analyze_website(domain) for domain in domains]
        results = await asyncio.gather(*tasks)
        execution_time = time.time() - start_time
        
        assert len(results) == 3
        assert execution_time < 120, "Concurrent analysis should complete within 2 minutes"
```

---

## 🔐 보안 고려사항

### API 보안
```python
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """JWT 토큰 검증"""
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

@app.post("/api/v1/analyze")
@limiter.limit("5/minute")  # 분당 5회 제한
async def analyze_website(request: Request, analysis_request: AnalysisRequest):
    # 분석 로직
    pass
```

### 입력 검증
```python
from pydantic import BaseModel, validator, HttpUrl
import re

class AnalysisRequest(BaseModel):
    url: HttpUrl
    
    @validator('url')
    def validate_url(cls, v):
        # 악의적 URL 패턴 차단
        blocked_patterns = [
            r'localhost',
            r'127\.0\.0\.1',
            r'192\.168\.',
            r'10\.',
            r'172\.(1[6-9]|2[0-9]|3[0-1])\.'
        ]
        
        url_str = str(v)
        for pattern in blocked_patterns:
            if re.search(pattern, url_str, re.IGNORECASE):
                raise ValueError(f'URL not allowed: {url_str}')
        
        return v
```

## 📋 최종 완성된 개발 PRD 요약

**AI/LLM 완전 배제 + Playwright 기반** 웹사이트 보안 분석 시스템 **SecureCheck Pro** 개발 PRD를 완성했습니다:

### 🎯 핵심 아키텍처
```
URL 입력 → Playwright 브라우저 시나리오 실행 → 네트워크 분석 → 
케이스 분류 → 고정 템플릿 선택 → 데이터 주입 → PDF 보고서 생성
```

### 🔑 핵심 특징
1. **Playwright 기반 실제 브라우저 테스트**: Chrome, Firefox, Safari 실제 경고 캡처
2. **40개 복합 케이스 분류**: SSL 케이스 5개 × 서버 상태 8개 조합  
3. **사전 정의된 시나리오 스크립트**: 모든 분석 로직이 고정된 스크립트
4. **결정론적 보고서**: 동일 입력 → 동일 템플릿 → 동일 PDF
5. **실제 스크린샷 포함**: 브라우저 경고 화면을 보고서에 포함

### 🛠️ 기술 스택
- **Browser Automation**: Playwright (핵심)
- **Backend**: FastAPI + PostgreSQL + Redis
- **Network Analysis**: OpenSSL + Python Socket
- **Template Engine**: Jinja2 + WeasyPrint
- **Frontend**: Next.js + TypeScript

### 📊 시나리오별 분석 로직
- **SSL 부재**: 포트 443 연결 실패 + 브라우저 "안전하지 않음" 캡처 → F등급
- **자체 서명**: Subject=Issuer + 브라우저 "비공개 연결 아님" 캡처 → D등급
- **406 서버오류**: HTTPS 접속 실패 + nginx Accept 헤더 문제 진단 → 복합 케이스  
- **만료**: 인증서 날짜 + 브라우저 "만료됨" 경고 → D등급
- **정상 SSL**: SSL Labs API + 브라우저 🔒 아이콘 확인 → A+~B등급

### 🎨 완성된 템플릿 시스템
```
templates/
├── base_template.html              # 공통 구조
├── no_ssl_template.html           # SSL 부재 (완성)
├── self_signed_template.html      # 자체서명+406오류 (완성)
├── components/
│   ├── executive_summary.html     # 경영진 요약 컴포넌트
│   ├── technical_analysis.html    # 기술 분석 컴포넌트  
│   └── business_impact.html       # 비즈니스 영향 컴포넌트
└── styles/
    └── report_styles.css          # PDF 최적화 스타일
```

### 🚀 핵심 차별점
- **완전한 자동화**: URL 입력만으로 전문가급 보고서 자동 생성
- **실제 브라우저 경험**: Playwright로 사용자가 보는 것과 동일한 경고 화면 캡처
- **복합 문제 대응**: SSL + 서버오류 등 실제 발생하는 복합 상황 분석
- **즉시 실행 가능**: 구체적 명령어와 코드가 포함된 실행 가이드

모든 분석이 **사전 정의된 스크립트와 템플릿**을 따르므로 **완전히 예측 가능하고 일관된 결과**를 보장하며, 
실제 브라우저 테스트로 **현실적이고 정확한 분석**을 제공합니다.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "프로젝트 구조 분석 및 기존 파일 확인", "status": "completed", "activeForm": "프로젝트 구조 분석 완료"}, {"content": "SSL 상태별 케이스 분류 및 분석", "status": "completed", "activeForm": "SSL 케이스 분류 완료"}, {"content": "고정 플로우 기반 UI/UX 시나리오 설계", "status": "completed", "activeForm": "고정 플로우 UI/UX 설계 완료"}, {"content": "케이스별 보고서 템플릿 정의", "status": "completed", "activeForm": "보고서 템플릿 정의 완료"}, {"content": "개발 PRD 문서 작성 (AI 제외)", "status": "completed", "activeForm": "개발 PRD 문서 작성 완료"}]

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "프로젝트 구조 분석 및 기존 파일 확인", "status": "completed", "activeForm": "프로젝트 구조 분석 완료"}, {"content": "SSL 상태별 케이스 분류 및 분석", "status": "completed", "activeForm": "SSL 케이스 분류 완료"}, {"content": "고정 플로우 기반 UI/UX 시나리오 설계", "status": "completed", "activeForm": "고정 플로우 UI/UX 설계 완료"}, {"content": "케이스별 보고서 템플릿 정의", "status": "completed", "activeForm": "보고서 템플릿 정의 완료"}, {"content": "개발 PRD 문서 작성 (AI 제외)", "status": "completed", "activeForm": "개발 PRD 문서 작성 완료"}]

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "프로젝트 구조 분석 및 기존 파일 확인", "status": "completed", "activeForm": "프로젝트 구조 분석 완료"}, {"content": "SSL 상태별 케이스 분류 및 분석", "status": "completed", "activeForm": "SSL 케이스 분류 완료"}, {"content": "고정 플로우 기반 UI/UX 시나리오 설계", "status": "completed", "activeForm": "고정 플로우 UI/UX 설계 완료"}, {"content": "케이스별 보고서 템플릿 정의", "status": "completed", "activeForm": "보고서 템플릿 정의 완료"}, {"content": "개발 PRD 문서 작성 (AI 제외)", "status": "in_progress", "activeForm": "개발 PRD 문서 작성 중"}]