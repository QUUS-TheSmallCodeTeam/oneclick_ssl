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
        alert('🎨 MD 디자인 요소가 적용된 PDF 보고서가 다운로드되었습니다!');
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
      // 분석 결과를 텍스트로 변환
      const reportContent = generateReportText(data);

      // Google Docs 생성 URL (간단한 방법)
      const baseUrl = 'https://docs.google.com/create';
      const title = encodeURIComponent(`${data.url.replace(/https?:\/\//, '')} - 보안 분석 보고서`);

      // 새 창에서 Google Docs 생성
      const newWindow = window.open(`${baseUrl}?title=${title}`, '_blank');

      // 약간의 지연 후 안내 메시지
      setTimeout(() => {
        // 클립보드에 보고서 내용 복사 시도
        if (navigator.clipboard) {
          navigator.clipboard.writeText(reportContent).then(() => {
            alert('Google Docs가 열렸습니다!\n\n보고서 내용이 클립보드에 복사되었습니다.\n\nCtrl+V (또는 Cmd+V)를 눌러 내용을 붙여넣으세요.');
          }).catch(() => {
            // 클립보드 복사 실패 시 내용 표시
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
    const lines = [
      `${data.url.replace(/https?:\/\//, '')} - 웹사이트 보안 분석 보고서`,
      '',
      `분석 일시: ${new Date(data.created_at).toLocaleString('ko-KR')}`,
      `SSL 등급: ${data.ssl_grade}`,
      `보안 점수: ${data.security_score}/100`,
      '',
      '=== 비즈니스 영향 분석 ===',
      '',
      `예상 연간 매출 손실: ₩${data.business_impact.revenue_loss_annual.toLocaleString()}`,
      `SEO 영향: -${data.business_impact.seo_impact}% 순위 하락`,
      `고객 신뢰도: -${data.business_impact.user_trust_impact}% 신뢰 손상`,
      '',
      '=== 발견된 보안 문제 ===',
      ''
    ];

    data.issues.forEach((issue, index) => {
      lines.push(`${index + 1}. ${issue.title} (${issue.severity.toUpperCase()})`);
      lines.push(`   ${issue.description}`);
      lines.push('');
    });

    if (data.recommendations.length > 0) {
      lines.push('=== 개선 권장사항 ===', '');

      data.recommendations.forEach((recommendation, index) => {
        lines.push(`${index + 1}. ${recommendation}`);
      });
    }

    return lines.join('\n');
  };

  return (
    <div className="space-y-6">
      {/* 요약 카드 */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-900">보안 분석 결과</h2>
          <div className="flex space-x-3">
            <button
              onClick={handleDownloadPDF}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
            >
              📄 PDF 다운로드
            </button>
            <button
              onClick={handleCreateGoogleDoc}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              📝 Google Docs 생성
            </button>
          </div>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-gray-500 mb-1">분석 대상</h3>
            <p className="text-lg font-semibold text-gray-900 truncate" title={data.url}>
              {data.url}
            </p>
          </div>
          
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-gray-500 mb-1">SSL 등급</h3>
            <p className="text-2xl font-bold text-blue-600">
              {data.ssl_grade}
            </p>
          </div>
          
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-gray-500 mb-1">보안 점수</h3>
            <p className={`text-2xl font-bold ${getScoreColor(data.security_score)}`}>
              {data.security_score}/100
            </p>
          </div>
          
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-gray-500 mb-1">발견된 문제</h3>
            <p className="text-2xl font-bold text-red-600">
              {data.issues.length}개
            </p>
          </div>
        </div>
      </div>

      {/* 비즈니스 영향 */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-xl font-bold text-gray-900 mb-4">비즈니스 영향 분석</h3>
        
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-red-50 p-4 rounded-lg border border-red-200">
            <h4 className="text-sm font-medium text-red-800 mb-2">예상 연간 매출 손실</h4>
            <p className="text-xl font-bold text-red-600">
              ₩{data.business_impact.revenue_loss_annual.toLocaleString()}
            </p>
          </div>
          
          <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
            <h4 className="text-sm font-medium text-yellow-800 mb-2">SEO 영향</h4>
            <p className="text-xl font-bold text-yellow-600">
              -{data.business_impact.seo_impact}% 순위 하락
            </p>
          </div>
          
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
            <h4 className="text-sm font-medium text-blue-800 mb-2">고객 신뢰도</h4>
            <p className="text-xl font-bold text-blue-600">
              -{data.business_impact.user_trust_impact}% 신뢰 손상
            </p>
          </div>
        </div>
      </div>

      {/* 발견된 문제들 */}
      {data.issues.length > 0 && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">발견된 보안 문제</h3>
          
          <div className="space-y-4">
            {data.issues.map((issue, index) => (
              <div
                key={index}
                className={`border rounded-lg p-4 ${getSeverityColor(issue.severity)}`}
              >
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold">{issue.title}</h4>
                  <span className="text-xs font-medium px-2 py-1 rounded uppercase">
                    {issue.severity}
                  </span>
                </div>
                <p className="text-sm opacity-90">{issue.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 개선 권장사항 */}
      {data.recommendations.length > 0 && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">개선 권장사항</h3>
          
          <div className="space-y-3">
            {data.recommendations.map((recommendation, index) => (
              <div key={index} className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium">
                  {index + 1}
                </span>
                <p className="text-gray-700">{recommendation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-center text-sm text-gray-500">
        분석 완료: {new Date(data.created_at).toLocaleString('ko-KR')}
      </div>
    </div>
  );
}