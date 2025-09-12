import { NextRequest, NextResponse } from 'next/server';
import { SSLAnalyzer } from '@/lib/ssl/analyzer';
import { SSL_GRADE_SCORES, BUSINESS_IMPACT_CONFIG, SECURITY_SCORING } from '@/lib/ssl/config';
import { SSLAnalysisResult, SecurityIssue, BusinessImpact } from '@/lib/ssl/types';

export async function POST(request: NextRequest) {
  try {
    const { url } = await request.json();
    
    if (!url) {
      return NextResponse.json(
        { error: 'URL이 필요합니다.' },
        { status: 400 }
      );
    }

    const analyzer = new SSLAnalyzer();
    const sslResult = await analyzer.analyze(url);
    
    // 보안 점수 계산
    const securityScore = calculateSecurityScore(sslResult);
    
    // 보안 이슈 추출
    const issues = extractSecurityIssues(sslResult);
    
    // 비즈니스 영향 계산
    const businessImpact = calculateBusinessImpact(sslResult);
    
    // 권장사항 생성
    const recommendations = generateRecommendations(sslResult);

    const result = {
      ssl_result: sslResult,
      security_score: securityScore,
      issues,
      business_impact: businessImpact,
      recommendations,
      analyzed_at: new Date().toISOString()
    };

    return NextResponse.json(result);
  } catch (error) {
    console.error('Analysis error:', error);
    return NextResponse.json(
      { error: '분석 중 오류가 발생했습니다.' },
      { status: 500 }
    );
  }
}

function calculateSecurityScore(sslResult: SSLAnalysisResult): number {
  const sslStatus = sslResult.ssl_status;
  
  if (sslStatus in SECURITY_SCORING.ssl_status_scores) {
    return SECURITY_SCORING.ssl_status_scores[sslStatus as keyof typeof SECURITY_SCORING.ssl_status_scores];
  } else if (sslStatus === 'valid') {
    const sslGrade = sslResult.ssl_grade;
    let score = SSL_GRADE_SCORES[sslGrade];
    
    score -= sslResult.missing_security_headers.length * SECURITY_SCORING.header_penalty;
    
    if (sslResult.days_until_expiry && sslResult.days_until_expiry < 30) {
      score -= SECURITY_SCORING.expiry_penalty;
    }
    
    return Math.max(0, score);
  } else {
    return 0;
  }
}

function extractSecurityIssues(sslResult: SSLAnalysisResult): SecurityIssue[] {
  const issues: SecurityIssue[] = [];
  const sslStatus = sslResult.ssl_status;

  if (sslStatus === 'no_ssl' || !sslResult.port_443_open) {
    issues.push(
      {
        type: 'ssl_service',
        severity: 'critical',
        title: 'HTTPS 서비스 완전 부재',
        description: '443 포트가 닫혀있어 HTTPS 서비스가 전혀 제공되지 않습니다.'
      },
      {
        type: 'data_encryption',
        severity: 'critical',
        title: '모든 데이터 평문 전송',
        description: '암호화 없이 모든 데이터가 평문으로 전송되어 도청 위험에 노출됩니다.'
      }
    );
  }

  if (sslStatus === 'expired') {
    issues.push({
      type: 'certificate',
      severity: 'critical',
      title: 'SSL 인증서 만료',
      description: 'SSL 인증서가 만료되어 브라우저에서 보안 경고를 표시합니다.'
    });
  }

  if (sslResult.is_self_signed) {
    issues.push({
      type: 'certificate',
      severity: 'high',
      title: '자체 서명 인증서',
      description: '신뢰할 수 있는 인증기관에서 발급하지 않은 인증서로, 브라우저에서 경고를 표시합니다.'
    });
  }

  if (sslResult.days_until_expiry && sslResult.days_until_expiry < 30) {
    issues.push({
      type: 'certificate',
      severity: sslResult.days_until_expiry < 7 ? 'critical' : 'medium',
      title: 'SSL 인증서 만료 임박',
      description: `SSL 인증서가 ${sslResult.days_until_expiry}일 후에 만료됩니다.`
    });
  }

  sslResult.missing_security_headers.forEach(header => {
    issues.push({
      type: 'security_header',
      severity: 'medium',
      title: `${header} 헤더 누락`,
      description: `${header} 보안 헤더가 설정되지 않았습니다.`
    });
  });

  return issues;
}

function calculateBusinessImpact(sslResult: SSLAnalysisResult): BusinessImpact {
  const grade = sslResult.ssl_grade;
  
  return {
    revenue_loss_annual: BUSINESS_IMPACT_CONFIG.revenue_loss_per_grade[grade],
    seo_impact: BUSINESS_IMPACT_CONFIG.seo_impact_per_grade[grade],
    user_trust_impact: BUSINESS_IMPACT_CONFIG.user_trust_impact_per_grade[grade]
  };
}

function generateRecommendations(sslResult: SSLAnalysisResult): Array<{title: string, description: string, priority: string}> {
  const recommendations = [];
  
  if (sslResult.ssl_grade === 'F' || sslResult.ssl_grade === 'D') {
    recommendations.push({
      title: 'SSL 구성 전면 검토',
      description: 'SSL 구성을 전면적으로 검토하고 최신 보안 프로토콜을 적용하세요.',
      priority: 'critical'
    });
  }

  if (sslResult.missing_security_headers.includes('Strict-Transport-Security')) {
    recommendations.push({
      title: 'HSTS 헤더 설정',
      description: 'HTTP Strict Transport Security 헤더를 설정하여 HTTPS 연결을 강제하세요.',
      priority: 'high'
    });
  }

  if (sslResult.missing_security_headers.includes('Content-Security-Policy')) {
    recommendations.push({
      title: 'CSP 헤더 설정',
      description: 'Content Security Policy 헤더를 설정하여 XSS 공격을 방지하세요.',
      priority: 'high'
    });
  }

  if (sslResult.days_until_expiry && sslResult.days_until_expiry < 60) {
    recommendations.push({
      title: '인증서 자동 갱신 시스템 구축',
      description: 'SSL 인증서 자동 갱신 시스템을 구축하여 만료를 방지하세요.',
      priority: 'medium'
    });
  }

  if (recommendations.length === 0) {
    recommendations.push({
      title: '정기적인 보안 점검',
      description: '정기적인 보안 점검을 통해 보안 상태를 유지하세요.',
      priority: 'low'
    });
  }

  return recommendations;
}