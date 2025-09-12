'use client';

interface AnalysisResult {
  id: string;
  url: string;
  ssl_grade: string;
  security_score: number;
  issues: Array<{
    type: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    title: string;
    description: string;
  }>;
  business_impact: {
    revenue_loss_annual: number;
    seo_impact: number;
    user_trust_impact: number;
  };
  recommendations: string[];
  created_at: string;
}

interface SecurityReportProps {
  data: AnalysisResult;
}

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'critical':
      return 'bg-red-100 text-red-800 border-red-200';
    case 'high':
      return 'bg-orange-100 text-orange-800 border-orange-200';
    case 'medium':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case 'low':
      return 'bg-green-100 text-green-800 border-green-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
};

const getScoreColor = (score: number) => {
  if (score >= 90) return 'text-green-600';
  if (score >= 70) return 'text-yellow-600';
  if (score >= 50) return 'text-orange-600';
  return 'text-red-600';
};

export function SecurityReport({ data }: SecurityReportProps) {
  const handleDownloadPDF = async () => {
    try {
      const response = await fetch(`/api/reports/${data.id}/download`);

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `security-report-${data.url.replace(/https?:\/\//, '')}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        alert('📄 보안 분석 보고서가 다운로드되었습니다!');
      } else {
        const errorText = await response.text();
        throw new Error(`PDF 다운로드 실패: ${errorText}`);
      }
    } catch (error) {
      console.error('PDF 다운로드 오류:', error);
      alert(`PDF 다운로드 중 오류가 발생했습니다: ${error.message}`);
    }
  };

  const handleCreateGoogleDoc = async () => {
    try {
      const reportContent = generateReportText(data);
      const baseUrl = 'https://docs.google.com/create';
      const title = encodeURIComponent(`${data.url.replace(/https?:\/\//, '')} - 웹사이트 보안 분석 보고서`);
      
      window.open(`${baseUrl}?title=${title}`, '_blank');

      setTimeout(() => {
        if (navigator.clipboard) {
          navigator.clipboard.writeText(reportContent).then(() => {
            alert('Google Docs가 열렸습니다!\n\n보고서 내용이 클립보드에 복사되었습니다.\n\nCtrl+V (또는 Cmd+V)를 눌러 내용을 붙여넣으세요.');
          }).catch(() => {
            alert('Google Docs가 열렸습니다!\n\n아래 내용을 복사해서 문서에 붙여넣으세요:\n\n' + reportContent);
          });
        } else {
          alert('Google Docs가 열렸습니다!\n\n아래 내용을 복사해서 문서에 붙여넣으세요:\n\n' + reportContent);
        }
      }, 2000);
    } catch (error) {
      console.error('Google Docs 생성 오류:', error);
      alert('Google Docs 생성 중 오류가 발생했습니다.');
    }
  };

  const generateReportText = (data: AnalysisResult): string => {
    const domain = data.url.replace(/https?:\/\//, '').replace(/\/$/, '');
    const analysisDate = new Date(data.created_at).toLocaleDateString('ko-KR');
    
    const lines = [
      `# ${domain.toUpperCase()} 웹사이트 보안 및 서버 설정 문제 분석 보고서`,
      '',
      `**분석 대상**: ${domain}`,
      `**분석 일시**: ${analysisDate}`,
      `**분석자**: Security Analysis Team`,
      `**보고서 버전**: 1.0`,
      '',
      '---',
      '',
      '## 📋 Executive Summary',
      '',
      `${domain} 웹사이트에 대한 보안 분석 결과, **중요한 보안 문제**가 발견되었습니다.`,
      '',
      '### 🚨 주요 발견사항',
      `- SSL 등급: **${data.ssl_grade}**`,
      `- 보안 점수: **${data.security_score}/100**`,
      `- 발견된 문제: **${data.issues.length}개**`,
      '',
      '### 💰 비즈니스 영향',
      `- **예상 연간 매출 손실**: ₩${data.business_impact.revenue_loss_annual.toLocaleString()}`,
      `- **SEO 영향**: -${data.business_impact.seo_impact}% 순위 하락`,
      `- **고객 신뢰도**: -${data.business_impact.user_trust_impact}% 신뢰 손상`,
      '',
      '---',
      '',
      '## 🔍 상세 기술 분석',
      ''
    ];

    if (data.issues.length > 0) {
      lines.push('### 🛡️ 보안 위험도 매트릭스', '');
      lines.push('| 취약점 | 심각도 | 설명 |');
      lines.push('|--------|--------|------|');
      
      data.issues.forEach((issue) => {
        const severityKorean = {
          'critical': '치명적',
          'high': '높음',
          'medium': '중간',
          'low': '낮음'
        }[issue.severity] || issue.severity;
        
        lines.push(`| **${issue.title}** | 🔴 **${severityKorean}** | ${issue.description} |`);
      });
      
      lines.push('', '---', '');
    }

    if (data.recommendations.length > 0) {
      lines.push('## 🔧 해결 방안 및 권장사항', '');
      lines.push('### Phase 1: 긴급 조치 (1-3일)', '');
      
      data.recommendations.forEach((recommendation, index) => {
        lines.push(`${index + 1}. **${recommendation}**`);
      });
      
      lines.push('', '---', '');
    }

    lines.push(
      '## 💰 비즈니스 영향 평가',
      '',
      '### 단기 영향 (1-3개월)',
      `- **예상 매출 손실**: ₩${data.business_impact.revenue_loss_annual.toLocaleString()}/년`,
      `- **SEO 순위 하락**: ${data.business_impact.seo_impact}%`,
      `- **고객 신뢰도 하락**: ${data.business_impact.user_trust_impact}%`,
      '',
      '---',
      '',
      '## 📞 실행 권장사항',
      '',
      '### 즉시 실행 (이번 주 내)',
      '1. **경영진 승인**: 보안 개선 프로젝트 승인',
      '2. **담당자 지정**: 내부 담당자 또는 외부 전문가 선정',
      '3. **예산 확보**: 보안 개선 예산 확보',
      '4. **일정 수립**: 구체적인 실행 일정 확정',
      '',
      '### 최종 권고',
      '**지금 즉시 행동하십시오.** 하루 늦을수록 고객 신뢰와 비즈니스 기회가 계속 손실됩니다.',
      '',
      '---',
      '',
      `**보고서 문의**: Security Analysis Team`,
      `**분석 완료**: ${new Date(data.created_at).toLocaleString('ko-KR')}`,
      '',
      '---',
      `*이 보고서는 ${analysisDate} 현재 상황을 기준으로 작성되었습니다.*`
    );

    return lines.join('\n');
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* 보고서 헤더 */}
      <div className="report-header bg-white rounded-lg shadow-lg p-8">
        <div className="text-center mb-6">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            {data.url.replace(/https?:\/\//, '').toUpperCase()} 웹사이트 보안 분석 보고서
          </h1>
          <div className="text-lg text-gray-600 space-y-1">
            <p><strong>분석 대상:</strong> {data.url}</p>
            <p><strong>분석 일시:</strong> {new Date(data.created_at).toLocaleString('ko-KR')}</p>
            <p><strong>분석자:</strong> Security Analysis Team</p>
            <p><strong>보고서 버전:</strong> 1.0</p>
          </div>
        </div>

        <div className="flex justify-center space-x-4 mb-8">
          <button
            onClick={handleDownloadPDF}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 font-medium"
          >
            📄 PDF 다운로드
          </button>
          <button
            onClick={handleCreateGoogleDoc}
            className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 font-medium"
          >
            📝 Google Docs 생성
          </button>
        </div>
      </div>

      {/* Executive Summary */}
      <div className="report-section">
        <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
          📋 Executive Summary
        </h2>
        <p className="text-lg text-gray-700 mb-6">
          {data.url.replace(/https?:\/\//, '')} 웹사이트에 대한 보안 분석 결과, <strong>중요한 보안 문제</strong>가 발견되었습니다.
        </p>

        <div className="grid md:grid-cols-2 gap-8">
          <div>
            <h3 className="text-xl font-semibold text-red-700 mb-4">🚨 주요 발견사항</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                <span className="font-medium">SSL 등급</span>
                <span className="text-xl font-bold text-blue-600">{data.ssl_grade}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                <span className="font-medium">보안 점수</span>
                <span className={`text-xl font-bold ${getScoreColor(data.security_score)}`}>
                  {data.security_score}/100
                </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                <span className="font-medium">발견된 문제</span>
                <span className="text-xl font-bold text-red-600">{data.issues.length}개</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-xl font-semibold text-orange-700 mb-4">💰 비즈니스 영향</h3>
            <div className="space-y-3">
              <div className="p-3 bg-red-50 border border-red-200 rounded">
                <div className="text-sm font-medium text-red-800">예상 연간 매출 손실</div>
                <div className="text-xl font-bold text-red-600">
                  ₩{data.business_impact.revenue_loss_annual.toLocaleString()}
                </div>
              </div>
              <div className="p-3 bg-yellow-50 border border-yellow-200 rounded">
                <div className="text-sm font-medium text-yellow-800">SEO 영향</div>
                <div className="text-xl font-bold text-yellow-600">
                  -{data.business_impact.seo_impact}% 순위 하락
                </div>
              </div>
              <div className="p-3 bg-blue-50 border border-blue-200 rounded">
                <div className="text-sm font-medium text-blue-800">고객 신뢰도</div>
                <div className="text-xl font-bold text-blue-600">
                  -{data.business_impact.user_trust_impact}% 신뢰 손상
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 상세 기술 분석 */}
      {data.issues.length > 0 && (
        <div className="report-section">
          <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
            🔍 상세 기술 분석
          </h2>
          
          <div className="mb-6">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">🛡️ 보안 위험도 매트릭스</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full bg-white border border-gray-300 rounded-lg">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600 border-b">취약점</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600 border-b">심각도</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600 border-b">영향도</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600 border-b">위험도</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {data.issues.map((issue, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900">{issue.title}</div>
                        <div className="text-sm text-gray-600">{issue.description}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          issue.severity === 'critical' ? 'bg-red-100 text-red-800' :
                          issue.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                          issue.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-green-100 text-green-800'
                        }`}>
                          {issue.severity === 'critical' ? '치명적' :
                           issue.severity === 'high' ? '높음' :
                           issue.severity === 'medium' ? '중간' : '낮음'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {issue.severity === 'critical' ? '치명적' :
                         issue.severity === 'high' ? '높음' :
                         issue.severity === 'medium' ? '중간' : '낮음'}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-sm font-medium ${
                          issue.severity === 'critical' || issue.severity === 'high' ? 'text-red-600' : 
                          issue.severity === 'medium' ? 'text-yellow-600' : 'text-green-600'
                        }`}>
                          {issue.severity === 'critical' || issue.severity === 'high' ? '🔴 High' :
                           issue.severity === 'medium' ? '🟡 Medium' : '🟢 Low'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 비즈니스 영향 평가 */}
      <div className="report-section">
        <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
          💰 비즈니스 영향 평가
        </h2>
        
        <div className="grid md:grid-cols-2 gap-8">
          <div>
            <h3 className="text-xl font-semibold text-gray-800 mb-4">단기 영향 (1-3개월)</h3>
            <div className="space-y-4">
              <div className="bg-red-50 border-l-4 border-red-400 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <div className="text-red-400 text-lg">📉</div>
                  </div>
                  <div className="ml-3">
                    <h4 className="text-sm font-medium text-red-800">웹사이트 트래픽 손실</h4>
                    <p className="mt-1 text-sm text-red-700">
                      보안 경고로 인한 이탈: 30-50%
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="bg-orange-50 border-l-4 border-orange-400 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <div className="text-orange-400 text-lg">💸</div>
                  </div>
                  <div className="ml-3">
                    <h4 className="text-sm font-medium text-orange-800">예상 매출 손실</h4>
                    <p className="mt-1 text-sm text-orange-700 font-bold">
                      ₩{data.business_impact.revenue_loss_annual.toLocaleString()}/년
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-xl font-semibold text-gray-800 mb-4">중장기 영향 (6개월 이상)</h3>
            <div className="space-y-4">
              <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <div className="text-yellow-400 text-lg">🔍</div>
                  </div>
                  <div className="ml-3">
                    <h4 className="text-sm font-medium text-yellow-800">SEO 및 검색 순위 하락</h4>
                    <p className="mt-1 text-sm text-yellow-700 font-bold">
                      -{data.business_impact.seo_impact}% 순위 하락
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <div className="text-blue-400 text-lg">🏢</div>
                  </div>
                  <div className="ml-3">
                    <h4 className="text-sm font-medium text-blue-800">브랜드 이미지 손상</h4>
                    <p className="mt-1 text-sm text-blue-700 font-bold">
                      -{data.business_impact.user_trust_impact}% 신뢰 손상
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 해결 방안 및 권장사항 */}
      {data.recommendations.length > 0 && (
        <div className="report-section">
          <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
            🔧 해결 방안 및 권장사항
          </h2>
          
          <div className="mb-6">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">Phase 1: 긴급 조치 (1-3일)</h3>
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <div className="flex items-center mb-2">
                <span className="text-red-600 text-lg mr-2">🚨</span>
                <span className="font-medium text-red-800">우선순위: ⭐⭐⭐⭐⭐ (Critical)</span>
              </div>
            </div>
            
            <div className="space-y-4">
              {data.recommendations.map((recommendation, index) => (
                <div key={index} className="flex items-start space-x-4 p-4 bg-white border border-gray-200 rounded-lg">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <p className="text-gray-800 font-medium">{recommendation}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 실행 권장사항 */}
      <div className="report-section">
        <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
          📞 실행 권장사항
        </h2>
        
        <div className="grid md:grid-cols-2 gap-8">
          <div>
            <h3 className="text-xl font-semibold text-gray-800 mb-4">즉시 실행 (이번 주 내)</h3>
            <div className="space-y-3">
              <div className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 bg-red-100 text-red-600 rounded-full flex items-center justify-center text-sm font-medium">1</span>
                <p className="text-gray-700"><strong>경영진 승인:</strong> 보안 개선 프로젝트 승인</p>
              </div>
              <div className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 bg-red-100 text-red-600 rounded-full flex items-center justify-center text-sm font-medium">2</span>
                <p className="text-gray-700"><strong>담당자 지정:</strong> 내부 담당자 또는 외부 전문가 선정</p>
              </div>
              <div className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 bg-red-100 text-red-600 rounded-full flex items-center justify-center text-sm font-medium">3</span>
                <p className="text-gray-700"><strong>예산 확보:</strong> 보안 개선 예산 확보</p>
              </div>
              <div className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 bg-red-100 text-red-600 rounded-full flex items-center justify-center text-sm font-medium">4</span>
                <p className="text-gray-700"><strong>일정 수립:</strong> 구체적인 실행 일정 확정</p>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-xl font-semibold text-red-700 mb-4">최종 권고</h3>
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <p className="text-red-800 font-medium text-lg">
                <strong>지금 즉시 행동하십시오.</strong> 하루 늦을수록 고객 신뢰와 비즈니스 기회가 계속 손실됩니다.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 보고서 푸터 */}
      <div className="report-section text-center bg-gray-50">
        <div className="space-y-2 text-sm text-gray-600">
          <p><strong>보고서 문의:</strong> Security Analysis Team</p>
          <p><strong>분석 완료:</strong> {new Date(data.created_at).toLocaleString('ko-KR')}</p>
          <p className="italic">
            *이 보고서는 {new Date(data.created_at).toLocaleDateString('ko-KR')} 현재 상황을 기준으로 작성되었습니다.*
          </p>
        </div>
      </div>
    </div>
  );
}