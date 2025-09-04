# SSL 인증서 상태 분석 가이드

웹사이트 접속만으로 SSL 인증서의 상태를 파악하고 문제점을 진단하는 종합적인 방법론을 제시합니다.

## 📋 목차
- [SSL 인증서 상태별 분류](#ssl-인증서-상태별-분류)
- [브라우저에서 즉시 확인하는 방법](#브라우저에서-즉시-확인하는-방법)
- [명령어를 통한 상세 분석](#명령어를-통한-상세-분석)
- [자체 서명 인증서 심화 분석](#자체-서명-인증서-심화-분석)
- [실제 사례 분석](#실제-사례-분석)
- [문제 해결 방안](#문제-해결-방안)

---

## SSL 인증서 상태별 분류

### 1️⃣ SSL 인증서가 아예 없는 경우
**증상:**
- 443 포트가 열려있지 않음
- HTTPS 접속 시도 시 연결 자체가 실패

**브라우저 오류:**
```
❌ ERR_CONNECTION_REFUSED
❌ ERR_SSL_PROTOCOL_ERROR
❌ "이 사이트에 연결할 수 없음"
```

**명령어 결과:**
```bash
curl -I https://example.com
# 결과: Connection refused

nc -z example.com 443
# 결과: Connection refused
```

### 2️⃣ SSL 인증서가 만료된 경우
**증상:**
- 인증서는 존재하지만 유효기간이 지남
- 과거에는 정상 작동했으나 현재는 오류

**브라우저 오류:**
```
❌ NET::ERR_CERT_DATE_INVALID
❌ "이 서버의 인증서가 만료되었습니다"
❌ 정확한 만료일시 표시됨
```

**명령어 결과:**
```bash
curl -I https://example.com
# 결과: SSL certificate problem: certificate has expired

echo | openssl s_client -connect example.com:443 | openssl x509 -noout -dates
# 결과: notAfter가 현재 날짜보다 이전
```

### 3️⃣ 자체 서명 인증서인 경우
**증상:**
- 인증서는 존재하고 유효하지만 신뢰할 수 없는 발급자
- 암호화는 되지만 신원 보증 없음

**브라우저 오류:**
```
❌ ERR_CERT_AUTHORITY_INVALID
❌ "이 서버의 인증서를 신뢰할 수 없습니다"
❌ "연결이 비공개가 아님"
```

**명령어 결과:**
```bash
curl -I https://example.com
# 결과: SSL certificate problem: self signed certificate

# subject와 issuer가 동일
echo | openssl s_client -connect example.com:443 | openssl x509 -noout -subject -issuer
# 결과: subject = issuer (자기가 자기를 서명)
```

### 4️⃣ 정상적인 SSL 인증서
**증상:**
- 신뢰할 수 있는 CA에서 발급
- 유효기간 내
- 도메인 일치

**브라우저 표시:**
```
✅ 🔒 자물쇠 아이콘
✅ "연결이 안전함"
✅ 인증서 세부정보 확인 가능
```

---

## 브라우저에서 즉시 확인하는 방법

### Chrome에서 확인
1. **주소창 확인**
   - 🔒 **초록색 자물쇠**: 정상
   - ⚠️ **경고 표시**: 문제 있음
   - 🚫 **연결 안전하지 않음**: SSL 없음 또는 만료

2. **자세한 정보 확인**
   - 자물쇠 아이콘 클릭 → "인증서" 클릭
   - 발급자, 유효기간, 주체 확인 가능

3. **개발자 도구 활용**
   - F12 → Security 탭
   - 인증서 상태 상세 분석

### Firefox에서 확인
- 주소창 자물쇠 아이콘 클릭
- "연결이 안전하지 않습니다" 경고 확인
- "인증서 보기"에서 상세 정보 확인

### Safari에서 확인
- 주소창 자물쇠 아이콘 클릭
- "인증서 보기" 선택
- 신뢰 설정 및 유효기간 확인

---

## 명령어를 통한 상세 분석

### 기본 연결 테스트
```bash
# 1. 443 포트 연결 테스트
nc -z example.com 443
echo $?  # 0이면 성공, 1이면 실패

# 2. SSL 연결 기본 테스트  
curl -I https://example.com

# 3. 상세 SSL 정보 확인
curl -vI https://example.com
```

### 인증서 정보 추출
```bash
# 인증서 기본 정보
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null | openssl x509 -noout -text

# 유효기간 확인
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null | openssl x509 -noout -dates

# 발급자와 주체 확인  
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null | openssl x509 -noout -subject -issuer

# 인증서 체인 확인
echo | openssl s_client -servername example.com -connect example.com:443 -showcerts 2>/dev/null
```

### 고급 분석
```bash
# SSL Labs 스타일 분석
nmap --script ssl-enum-ciphers -p 443 example.com

# 인증서 만료일까지 남은 일수 계산
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null | openssl x509 -noout -checkend 0

# 특정 일수 후 만료 여부 (30일)
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null | openssl x509 -noout -checkend 2592000
```

---

## 자체 서명 인증서 심화 분석

### 자체 서명 인증서란?
제3자 인증기관(CA) 없이 자기 자신이 발급하고 서명한 인증서입니다.

**신뢰 체계 비교:**
- **정상 인증서**: 웹사이트 ← CA(인증기관) ← 루트CA ← 브라우저 신뢰
- **자체 서명**: 웹사이트 ← 자기 자신 ← ❌ 브라우저 불신

### 식별 방법
```bash
# subject와 issuer 비교
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -subject -issuer

# 결과 해석:
# 자체 서명: subject = issuer (동일)
# 정상 인증서: subject ≠ issuer (다름)
```

### 자체 서명 인증서를 사용하는 이유
1. **비용 절약**: 상용 SSL 인증서 연간 비용 절약
2. **내부 시스템**: 외부 접근이 없는 사내 네트워크
3. **개발/테스트**: 프로덕션 환경이 아닌 개발 단계
4. **임시 조치**: 급하게 HTTPS 적용 필요시
5. **기술적 이해 부족**: SSL 인증서 구매/설정 방법 모름

### 보안상 위험성
1. **중간자 공격(MITM) 취약성**
   - 공격자가 가짜 인증서로 트래픽 가로채기 가능
   - 사용자는 진짜 사이트와 구별하기 어려움

2. **신원 확인 불가**
   - 해당 도메인의 실제 소유자인지 확인 불가
   - 피싱 사이트와 구별 어려움

3. **사용자 신뢰도 하락**
   - 브라우저 경고 메시지로 인한 사용자 이탈
   - 전문성 부족으로 인식될 가능성

---

## 실제 사례 분석

### 사례 1: TSC 사이트 (tsccom.co.kr)

**접속 테스트 결과:**
```bash
# HTTP 접속
curl -I http://tsccom.co.kr/html/index.html
# 결과: 200 OK (정상 접속)

# HTTPS 접속
curl -I https://tsccom.co.kr
# 결과: SSL certificate problem: self signed certificate

# 인증서 분석
echo | openssl s_client -connect tsccom.co.kr:443 2>/dev/null | openssl x509 -noout -subject -issuer
# 결과: 
# subject=C=GB, ST=Berkshire, L=Newbury, O=My Company Ltd
# issuer=C=GB, ST=Berkshire, L=Newbury, O=My Company Ltd
```

**분석 결과:**
- ✅ HTTP로는 정상 접속 가능
- ❌ HTTPS는 자체 서명 인증서로 인한 오류
- 🔍 subject = issuer (자체 서명 확인)
- 📅 유효기간: 2017-2117 (100년짜리 테스트용으로 추정)

**개선 권장사항:**
1. Let's Encrypt 무료 SSL 인증서 적용
2. 기존 자체 서명 인증서 제거
3. HTTPS 리다이렉션 설정

### 사례 2: 정상 사이트 (google.com)

**인증서 분석:**
```bash
echo | openssl s_client -connect google.com:443 2>/dev/null | openssl x509 -noout -subject -issuer
# 결과:
# subject=CN=*.google.com  
# issuer=C=US, O=Google Trust Services, CN=WE2
```

**분석 결과:**
- ✅ subject ≠ issuer (정상 CA 서명)
- ✅ 와일드카드 인증서 (*.google.com)
- ✅ 신뢰할 수 있는 CA (Google Trust Services)

---

## 문제 해결 방안

### 웹사이트 운영자 관점

#### 1. 무료 SSL 인증서 적용
**Let's Encrypt 사용:**
```bash
# Certbot 설치 (Ubuntu/Debian)
sudo apt update
sudo apt install certbot python3-certbot-apache

# 인증서 발급 및 설치
sudo certbot --apache -d example.com

# 자동 갱신 설정
sudo crontab -e
# 추가: 0 12 * * * /usr/bin/certbot renew --quiet
```

**장점:**
- 완전 무료
- 3개월 자동 갱신
- 모든 브라우저에서 신뢰
- 간단한 설치 과정

#### 2. 상용 SSL 인증서 구매
**추천 제공업체:**
- Comodo/Sectigo: 가성비 우수
- DigiCert: 프리미엄 브랜드
- GlobalSign: 글로벌 인지도

**가격대:**
- DV (Domain Validation): 연간 1-5만원
- OV (Organization Validation): 연간 10-30만원  
- EV (Extended Validation): 연간 50-100만원

#### 3. 클라우드 서비스 활용
**Cloudflare:**
- 무료 SSL 프록시 제공
- CDN 및 DDoS 보호 포함
- 간단한 DNS 설정만으로 적용

**AWS Certificate Manager:**
- AWS 리소스와 함께 사용시 무료
- 자동 갱신
- Load Balancer, CloudFront 통합

#### 4. 서버 설정 개선
```nginx
# Nginx SSL 설정 예시
server {
    listen 443 ssl http2;
    server_name example.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    # 보안 강화 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    # HSTS 헤더
    add_header Strict-Transport-Security "max-age=63072000" always;
}

# HTTP → HTTPS 리다이렉션
server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}
```

### 사용자 관점

#### 1. 위험도 평가
**낮은 위험 (진행 가능):**
- 내부 시스템, 개발 환경
- 민감한 정보 입력하지 않는 경우
- 신뢰할 수 있는 출처에서 확인된 사이트

**높은 위험 (접속 금지):**
- 로그인, 개인정보 입력 필요한 사이트
- 금융, 쇼핑몰 등 민감한 거래
- 출처를 확신할 수 없는 사이트

#### 2. 임시 접속 방법
**Chrome에서:**
1. "고급" 클릭
2. "안전하지 않은 사이트로 이동" 클릭
3. ⚠️ 위험을 인지하고 진행

**Firefox에서:**
1. "고급..." 클릭  
2. "위험을 감수하고 계속" 클릭
3. "예외 추가" 확인

#### 3. 안전한 대안
- VPN 사용으로 트래픽 보호
- 개인정보 입력 금지
- 웹사이트 운영자에게 정상 SSL 설치 요청
- 모바일 앱이나 다른 접속 방법 확인

---

## 자동화 스크립트

### SSL 상태 일괄 체크 스크립트
```bash
#!/bin/bash
# ssl_check.sh

check_ssl() {
    local domain=$1
    local port=${2:-443}
    
    echo "=== SSL Check for $domain:$port ==="
    
    # 1. 포트 연결 테스트
    if nc -z -w5 $domain $port 2>/dev/null; then
        echo "✅ Port $port is open"
    else
        echo "❌ Port $port is closed or filtered"
        return 1
    fi
    
    # 2. 인증서 정보 추출
    local cert_info=$(echo | timeout 10 openssl s_client -servername $domain -connect $domain:$port 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        # 유효기간 확인
        echo "$cert_info" | openssl x509 -noout -dates 2>/dev/null
        
        # 발급자 확인
        local subject=$(echo "$cert_info" | openssl x509 -noout -subject 2>/dev/null)
        local issuer=$(echo "$cert_info" | openssl x509 -noout -issuer 2>/dev/null)
        
        echo "$subject"
        echo "$issuer"
        
        # 자체 서명 여부 확인
        if [ "$subject" = "$issuer" ]; then
            echo "⚠️ Self-signed certificate detected"
        else
            echo "✅ Certificate signed by CA"
        fi
        
        # 만료일 확인
        local expire_check=$(echo "$cert_info" | openssl x509 -noout -checkend 2592000 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo "✅ Certificate valid for more than 30 days"
        else
            echo "⚠️ Certificate expires within 30 days"
        fi
    else
        echo "❌ Unable to retrieve certificate information"
    fi
    
    echo ""
}

# 사용법
check_ssl "google.com"
check_ssl "tsccom.co.kr"  
check_ssl "expired.badssl.com"
check_ssl "self-signed.badssl.com"
```

### 대량 사이트 SSL 상태 모니터링
```bash
#!/bin/bash
# bulk_ssl_check.sh

# 확인할 도메인 목록
domains=(
    "google.com"
    "github.com"
    "stackoverflow.com"
    "badssl.com"
    "expired.badssl.com"
    "self-signed.badssl.com"
)

# 결과 파일
output_file="ssl_check_results_$(date +%Y%m%d_%H%M%S).csv"
echo "Domain,Port,Status,Certificate_Type,Days_Until_Expiry,Issuer" > $output_file

for domain in "${domains[@]}"; do
    echo "Checking $domain..."
    
    # 간단한 상태 체크 함수 호출
    result=$(check_ssl_simple "$domain")
    echo "$result" >> $output_file
done

echo "Results saved to: $output_file"
```

---

## 결론

SSL 인증서 상태 분석은 웹사이트의 보안성과 신뢰성을 평가하는 중요한 과정입니다. 

### 핵심 포인트:
1. **브라우저만으로도** SSL 상태를 즉시 파악할 수 있습니다
2. **명령어 도구**를 활용하면 더 상세한 분석이 가능합니다  
3. **자체 서명 인증서**는 암호화는 제공하지만 신뢰성은 보장하지 않습니다
4. **Let's Encrypt** 같은 무료 SSL을 활용하여 쉽게 문제를 해결할 수 있습니다

### 권장 사항:
- **운영자**: 무료 SSL 인증서로 업그레이드
- **사용자**: 위험도를 평가하여 신중하게 접속 결정
- **개발자**: 자동화된 SSL 모니터링 시스템 구축

이 가이드를 통해 SSL 인증서의 상태를 정확히 파악하고, 적절한 대응 방안을 수립할 수 있을 것입니다.