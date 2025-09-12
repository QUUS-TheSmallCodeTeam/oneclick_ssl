'use client';

import React from 'react';
import { SSLAnalysisResult, SecurityIssue, BusinessImpact } from '@/lib/ssl/types';

interface SecurityReportProps {
  data: {
    ssl_result: SSLAnalysisResult;
    security_score: number;
    issues: SecurityIssue[];
    business_impact: BusinessImpact;
    recommendations: Array<{title: string, description: string, priority: string}>;
    analyzed_at: string;
  };
}

export default function TSCSecurityReport({ data }: SecurityReportProps) {
  const { ssl_result, security_score, issues, business_impact, recommendations } = data;

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'rgb(40, 167, 69)';
    if (score >= 60) return 'rgb(255, 193, 7)';
    return 'rgb(220, 53, 69)';
  };

  const getGradeColor = (grade: string) => {
    switch (grade.toLowerCase()) {
      case 'a+':
      case 'a': return '#28a745';
      case 'b': return '#ffc107';
      case 'c': return '#fd7e14';
      case 'd':
      case 'f': return '#dc3545';
      default: return '#dc3545';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#dc3545';
      case 'high': return '#fd7e14';
      case 'medium': return '#ffc107';
      case 'low': return '#28a745';
      default: return '#6c757d';
    }
  };

  const handlePrintReport = () => {
    window.print();
  };

  return (
    <div className="security-report">
      <style jsx>{`
        @media print {
          .no-print { display: none !important; }
          .page-break { page-break-before: always; }
          .avoid-break { page-break-inside: avoid; }
          body { font-size: 11px; }
        }
        
        @page {
          size: A4;
          margin: 2cm;
        }
        
        .security-report {
          font-family: 'Noto Sans KR', 'Malgun Gothic', Arial, sans-serif;
          line-height: 1.6;
          color: #333;
          max-width: 800px;
          margin: 0 auto;
          padding: 20px;
          background: white;
        }
        
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
          box-shadow: 0 2px 10px rgba(0,123,255,0.3);
        }
        
        .report-header {
          border-bottom: 3px solid #007bff;
          margin-bottom: 30px;
          padding-bottom: 20px;
          page-break-inside: avoid;
        }
        
        .report-header h1 {
          color: #007bff;
          font-size: 28px;
          margin-bottom: 15px;
          font-weight: bold;
          text-align: center;
        }
        
        .header-meta {
          display: flex;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 20px;
        }
        
        .meta-item {
          margin: 5px 0;
          font-size: 14px;
        }
        
        .grade-badge {
          display: inline-block;
          padding: 6px 12px;
          border-radius: 4px;
          color: white;
          font-weight: bold;
          font-size: 16px;
          margin-left: 8px;
        }
        
        .section {
          margin: 40px 0;
          page-break-inside: avoid;
        }
        
        .section h2 {
          color: #007bff;
          font-size: 20px;
          margin-bottom: 20px;
          border-left: 4px solid #007bff;
          padding-left: 15px;
          font-weight: bold;
        }
        
        .score-circle {
          display: inline-block;
          width: 120px;
          height: 120px;
          border-radius: 50%;
          border: 6px solid;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          margin: 20px auto;
          background: rgba(255,255,255,0.9);
        }
        
        .score-number {
          font-size: 32px;
          font-weight: bold;
        }
        
        .score-label {
          font-size: 14px;
          margin-top: 5px;
        }
        
        .issue-item {
          margin: 15px 0;
          padding: 15px;
          border-left: 4px solid;
          border-radius: 4px;
          background: rgba(0,0,0,0.02);
        }
        
        .issue-title {
          font-weight: bold;
          margin-bottom: 8px;
        }
        
        .business-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 20px;
          margin: 20px 0;
        }
        
        .impact-card {
          padding: 20px;
          border: 1px solid #dee2e6;
          border-radius: 8px;
          text-align: center;
          background: white;
        }
        
        .rec-item {
          margin: 20px 0;
          padding: 15px;
          border: 1px solid #dee2e6;
          border-radius: 6px;
          background: rgba(0,0,0,0.01);
        }
        
        .priority-badge {
          display: inline-block;
          padding: 4px 8px;
          border-radius: 4px;
          color: white;
          font-size: 12px;
          font-weight: bold;
          text-transform: uppercase;
        }
        
        .footer {
          margin-top: 60px;
          padding-top: 20px;
          border-top: 1px solid #ddd;
          font-size: 12px;
          color: #666;
          text-align: center;
        }
      `}</style>
      
      <button className="print-button no-print" onClick={handlePrintReport}>
        🖨️ PDF 다운로드
      </button>
      
      {/* 보고서 헤더 */}
      <div className="report-header avoid-break">
        <h1>{ssl_result.domain} 웹사이트 보안 분석 보고서</h1>
        <div className="header-meta">
          <div>
            <div className="meta-item">
              <strong>분석 대상:</strong> {ssl_result.domain}
            </div>
            <div className="meta-item">
              <strong>분석 일시:</strong> {new Date(ssl_result.analyzed_at).toLocaleString('ko-KR')}
            </div>
          </div>
          <div>
            <div className="meta-item">
              <strong>분석 도구:</strong> SecureCheck Pro
            </div>
            <div className="meta-item">
              <strong>보안 등급:</strong>
              <span 
                className="grade-badge" 
                style={{ backgroundColor: getGradeColor(ssl_result.ssl_grade) }}
              >
                {ssl_result.ssl_grade}
              </span>
            </div>
          </div>
        </div>
      </div>
      
      {/* 보안 점수 개요 */}
      <div className="section avoid-break" style={{ textAlign: 'center' }}>
        <h2>📊 보안 점수 개요</h2>
        <div 
          className="score-circle"
          style={{ 
            borderColor: getScoreColor(security_score),
            color: getScoreColor(security_score)
          }}
        >
          <div className="score-number">{security_score}/100</div>
          <div className="score-label">보안 점수</div>
        </div>
      </div>
      
      {/* Executive Summary */}
      <div className="section avoid-break">
        <h2>📋 Executive Summary</h2>
        <div style={{ padding: '20px', background: '#f8f9fa', borderRadius: '8px' }}>
          <p>
            <strong>{ssl_result.domain}</strong>에 대한 보안 분석 결과, 
            전체 보안 점수는 <strong>{security_score}점</strong>이며 
            SSL 등급은 <strong>{ssl_result.ssl_grade}</strong>로 평가되었습니다.
          </p>
          <p>
            총 <strong>{issues.length}개의 보안 이슈</strong>가 발견되었으며, 
            이 중 {issues.filter(i => i.severity === 'critical').length}개가 치명적 수준, 
            {issues.filter(i => i.severity === 'high').length}개가 높은 수준의 위험도로 분류됩니다.
          </p>
        </div>
      </div>
      
      {/* 발견된 보안 문제 */}
      <div className="section">
        <h2>🚨 발견된 보안 문제</h2>
        {issues.length > 0 ? (
          <>
            <p style={{ marginBottom: '20px', fontWeight: 'bold' }}>
              총 {issues.length}개의 보안 문제가 발견되었습니다.
            </p>
            {issues.map((issue, index) => (
              <div 
                key={index}
                className="issue-item"
                style={{ borderLeftColor: getSeverityColor(issue.severity) }}
              >
                <div 
                  className="issue-title"
                  style={{ color: getSeverityColor(issue.severity) }}
                >
                  [{issue.severity.toUpperCase()}] {issue.title}
                </div>
                <p style={{ margin: 0, fontSize: '14px' }}>{issue.description}</p>
              </div>
            ))}
          </>
        ) : (
          <div style={{ 
            padding: '20px', 
            background: '#d4edda', 
            border: '1px solid #c3e6cb', 
            borderRadius: '8px',
            color: '#155724'
          }}>
            ✅ <strong>심각한 보안 문제가 발견되지 않았습니다.</strong>
          </div>
        )}
      </div>
      
      {/* 비즈니스 영향 */}
      <div className="section avoid-break">
        <h2>💰 비즈니스 영향</h2>
        <div className="business-grid">
          {business_impact.revenue_loss_annual && (
            <div className="impact-card">
              <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '10px', color: '#666' }}>
                예상 연간 매출 손실
              </div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#dc3545' }}>
                ₩{business_impact.revenue_loss_annual.toLocaleString()}
              </div>
            </div>
          )}
          {business_impact.seo_impact && (
            <div className="impact-card">
              <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '10px', color: '#666' }}>
                SEO 순위 영향
              </div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#fd7e14' }}>
                -{business_impact.seo_impact}%
              </div>
            </div>
          )}
          {business_impact.user_trust_impact && (
            <div className="impact-card">
              <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '10px', color: '#666' }}>
                사용자 신뢰도 영향
              </div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#ffc107' }}>
                -{business_impact.user_trust_impact}%
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* 개선 권장사항 */}
      <div className="section">
        <h2>🛠️ 개선 권장사항</h2>
        {recommendations.map((rec, index) => (
          <div key={index} className="rec-item">
            <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>{rec.title}</div>
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '10px' }}>
              {rec.description}
            </div>
            <span 
              className="priority-badge"
              style={{ backgroundColor: getSeverityColor(rec.priority) }}
            >
              {rec.priority}
            </span>
          </div>
        ))}
      </div>
      
      {/* 푸터 */}
      <div className="footer">
        <p>본 보고서는 SecureCheck Pro에 의해 자동 생성되었습니다 | 생성일시: {new Date().toLocaleString('ko-KR')}</p>
        <p>⚠️ 이 보고서는 분석 시점 기준이며, 웹사이트 변경시 재분석이 필요합니다</p>
      </div>
    </div>
  );
}