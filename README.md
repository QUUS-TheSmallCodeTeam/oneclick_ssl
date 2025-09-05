# 원클릭 SSL체크

웹사이트의 SSL/TLS 보안을 간편하게 분석하고 상세한 보고서를 생성하는 보안 분석 도구입니다.

## 📋 프로젝트 개요

이 프로젝트는 웹사이트의 SSL/TLS 보안을 원클릭으로 분석하여 다음과 같은 기능을 제공합니다:

- **SSL/TLS 인증서 분석**: 인증서 유효성, 만료일, 보안 수준 평가
- **보안 헤더 분석**: HTTP 보안 헤더의 존재 여부 및 적절성 검토
- **취약점 스캔**: 알려진 SSL/TLS 관련 취약점 탐지
- **보고서 생성**: 분석 결과를 전문적인 PDF 보고서로 변환

## 🏗️ 프로젝트 구조

```
원클릭SSL체크/
├── securecheck-pro/          # 메인 애플리케이션
│   ├── backend/             # Python FastAPI 백엔드 서버
│   │   ├── main.py         # 메인 서버 파일
│   │   ├── ssl_analyzer.py # SSL 분석 모듈
│   │   ├── report_generator.py # 보고서 생성 모듈
│   │   └── requirements.txt # Python 의존성
│   ├── frontend/            # Next.js 프론트엔드
│   │   ├── src/
│   │   ├── package.json
│   │   └── tsconfig.json
│   └── shared/              # 공통 코드 및 타입 정의
├── templates/               # 보고서 템플릿
│   ├── base_template.html
│   ├── components/
│   └── styles/
└── *.md                     # 프로젝트 문서
```

## 🚀 빠른 시작

### 백엔드 실행 (권장)

```bash
cd securecheck-pro/backend

# 가상환경 생성 및 활성화 (권장)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는 venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn main:app --reload
```

서버가 `http://localhost:8000`에서 실행됩니다.

### 프론트엔드 실행

```bash
cd securecheck-pro/frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

프론트엔드가 `http://localhost:3000`에서 실행됩니다.

## 📖 API 문서

백엔드 서버 실행 후 다음 주소에서 API 문서를 확인할 수 있습니다:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🛠️ 주요 기능

### SSL/TLS 분석
- 인증서 유효성 검증
- 만료일 모니터링
- 암호화 강도 평가
- 인증서 체인 검증

### 보안 헤더 분석
- HTTP 보안 헤더 점검
- CSP (Content Security Policy) 검토
- HSTS 설정 확인
- X-Frame-Options 등 보안 헤더 분석

### 보고서 생성
- PDF 형식의 전문 보고서
- 실행 요약 및 상세 분석
- 개선 권장사항 제시
- 시각적 차트 및 그래프

## 📋 요구사항

### 백엔드
- Python 3.8+
- FastAPI
- Uvicorn
- ReportLab (PDF 생성)
- 추가 의존성은 `requirements.txt` 참고

### 프론트엔드
- Node.js 16+
- Next.js 13+
- TypeScript
- 추가 의존성은 `package.json` 참고

## 🔧 설정

### 환경 변수

백엔드의 환경 변수를 `.env` 파일에 설정할 수 있습니다:

```env
# 데이터베이스 설정 (선택사항)
DATABASE_URL=sqlite:///./security_analyzer.db

# Redis 설정 (선택사항)
REDIS_URL=redis://localhost:6379

# 환경 설정
ENVIRONMENT=development
```

## 📊 사용법

1. 프론트엔드에서 분석할 웹사이트 URL 입력
2. 분석 시작 버튼 클릭
3. 실시간으로 분석 진행 상황 확인
4. 분석 완료 후 상세 보고서 다운로드

## 🐳 Docker 배포

### Hugging Face Spaces 배포

이 프로젝트는 Hugging Face Spaces에 배포할 수 있도록 구성되어 있습니다. 단일 컨테이너에서 FastAPI 백엔드와 React 프론트엔드를 모두 제공합니다.

```bash
cd securecheck-pro
docker build -t securecheck-pro .
docker run -p 7860:7860 securecheck-pro
```

애플리케이션이 `http://localhost:7860`에서 실행됩니다.

### 배포 구조
- **FastAPI 백엔드**: API 엔드포인트 제공 (`/api/v1/*`)
- **React 프론트엔드**: 정적 파일로 FastAPI를 통해 서비스 (`/`, `/static/*`)
- **단일 포트**: 7860 (Hugging Face Spaces 표준)

### 로컬 개발 (권장)

로컬 개발 시에는 Docker 없이 백엔드와 프론트엔드를 별도로 실행하는 것을 권장합니다.

## 📝 개발 문서

프로젝트와 관련된 상세 문서는 다음 파일들을 참고하세요:

- `PRD_Website_Security_Analyzer.md` - 제품 요구사항 문서
- `Development_PRD_SecureCheck_Pro.md` - 개발 요구사항
- `SSL_Certificate_Analysis_Guide.md` - SSL 분석 가이드
- `TSC_Website_Security_Analysis_Report.md` - 보안 분석 보고서 템플릿

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 문의

프로젝트에 대한 질문이나 제안사항이 있으시면 이슈를 생성해 주세요.
