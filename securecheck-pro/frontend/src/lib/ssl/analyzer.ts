import { TLSSocket } from 'tls';
import * as tls from 'tls';
import * as net from 'net';
import axios from 'axios';
import { SSLAnalysisResult, SecurityIssue } from './types';
import { SECURITY_HEADERS, SSL_GRADE_SCORES, CERTIFICATE_THRESHOLDS } from './config';

export class SSLAnalyzer {
  private securityHeaders = SECURITY_HEADERS;

  async analyze(url: string): Promise<SSLAnalysisResult> {
    const parsedUrl = new URL(url.startsWith('http') ? url : `https://${url}`);
    const domain = parsedUrl.hostname;
    const port = 443;

    const result: SSLAnalysisResult = {
      domain,
      port,
      analyzed_at: new Date().toISOString(),
      url_scheme: parsedUrl.protocol.slice(0, -1),
      port_443_open: false,
      ssl_grade: 'F',
      certificate_valid: false,
      ssl_status: 'connection_error',
      analysis_result: '분석 실패',
      missing_security_headers: [],
      hsts_enabled: false,
      security_headers: {}
    };

    try {
      // 1. 포트 연결 테스트
      const portStatus = await this.testPortConnection(domain, port);
      result.port_443_open = portStatus;

      if (!portStatus) {
        result.ssl_status = 'no_ssl';
        result.analysis_result = 'SSL 인증서가 아예 없는 경우';
        result.missing_security_headers = [...this.securityHeaders];
        return result;
      }

      // 2. SSL/TLS 연결 및 인증서 정보 가져오기
      const sslInfo = await this.getSSLInfo(domain, port);
      Object.assign(result, sslInfo);

      // 3. 보안 헤더 확인
      const headerInfo = await this.checkSecurityHeaders(`https://${domain}`);
      result.missing_security_headers = headerInfo.missing_headers;
      result.security_headers = headerInfo.headers;
      result.hsts_enabled = headerInfo.hsts_enabled;

      // 4. SSL 등급 계산
      result.ssl_grade = this.calculateSSLGrade(result);

      return result;
    } catch (error) {
      console.error('SSL analysis error:', error);
      result.analysis_result = `분석 중 오류: ${error instanceof Error ? error.message : 'Unknown error'}`;
      return result;
    }
  }

  private async testPortConnection(domain: string, port: number): Promise<boolean> {
    return new Promise((resolve) => {
      const socket = new net.Socket();
      const timeout = 5000;

      socket.setTimeout(timeout);
      
      socket.on('connect', () => {
        socket.destroy();
        resolve(true);
      });

      socket.on('timeout', () => {
        socket.destroy();
        resolve(false);
      });

      socket.on('error', () => {
        resolve(false);
      });

      socket.connect(port, domain);
    });
  }

  private async getSSLInfo(domain: string, port: number): Promise<Partial<SSLAnalysisResult>> {
    return new Promise((resolve, reject) => {
      const options = {
        host: domain,
        port: port,
        rejectUnauthorized: false, // 자체서명 인증서도 정보를 가져오기 위해
        servername: domain
      };

      const socket = tls.connect(options, () => {
        const cert = socket.getPeerCertificate(true);
        const cipher = socket.getCipher();
        
        if (!cert || Object.keys(cert).length === 0) {
          socket.end();
          resolve({
            ssl_status: 'connection_error',
            certificate_valid: false,
            analysis_result: '인증서 정보를 가져올 수 없습니다'
          });
          return;
        }

        const now = new Date();
        const validFrom = new Date(cert.valid_from);
        const validTo = new Date(cert.valid_to);
        const daysUntilExpiry = Math.floor((validTo.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
        
        let sslStatus: SSLAnalysisResult['ssl_status'] = 'valid';
        let certificateValid = true;
        let analysisResult = '유효한 SSL 인증서';

        // 인증서 상태 확인
        if (now > validTo) {
          sslStatus = 'expired';
          certificateValid = false;
          analysisResult = '만료된 SSL 인증서';
        } else if (cert.issuer.CN === cert.subject.CN) {
          sslStatus = 'self_signed';
          certificateValid = false;
          analysisResult = '자체 서명된 SSL 인증서';
        } else if (socket.authorized === false) {
          sslStatus = 'verify_failed';
          certificateValid = false;
          analysisResult = 'SSL 인증서 검증 실패';
        }

        const result = {
          ssl_status: sslStatus,
          certificate_valid: certificateValid,
          analysis_result: analysisResult,
          days_until_expiry: daysUntilExpiry,
          is_self_signed: cert.issuer.CN === cert.subject.CN,
          certificate_issuer: cert.issuer.CN || cert.issuer.O || 'Unknown',
          certificate_subject: cert.subject.CN || 'Unknown',
          certificate_start_date: cert.valid_from,
          certificate_end_date: cert.valid_to
        };

        socket.end();
        resolve(result);
      });

      socket.on('error', (error) => {
        resolve({
          ssl_status: 'connection_error',
          certificate_valid: false,
          analysis_result: `SSL 연결 오류: ${error.message}`
        });
      });

      socket.setTimeout(10000, () => {
        socket.destroy();
        resolve({
          ssl_status: 'connection_error',
          certificate_valid: false,
          analysis_result: 'SSL 연결 시간 초과'
        });
      });
    });
  }

  private async checkSecurityHeaders(url: string): Promise<{
    missing_headers: string[];
    headers: Record<string, string>;
    hsts_enabled: boolean;
  }> {
    try {
      const response = await axios.get(url, {
        timeout: 10000,
        validateStatus: () => true, // 모든 상태 코드 허용
        maxRedirects: 5
      });

      const headers = response.headers;
      const securityHeaders: Record<string, string> = {};
      const missingHeaders: string[] = [];

      for (const header of this.securityHeaders) {
        const headerValue = headers[header.toLowerCase()];
        if (headerValue) {
          securityHeaders[header] = headerValue;
        } else {
          missingHeaders.push(header);
        }
      }

      const hstsEnabled = !!headers['strict-transport-security'];

      return {
        missing_headers: missingHeaders,
        headers: securityHeaders,
        hsts_enabled: hstsEnabled
      };
    } catch (error) {
      return {
        missing_headers: [...this.securityHeaders],
        headers: {},
        hsts_enabled: false
      };
    }
  }

  private calculateSSLGrade(result: SSLAnalysisResult): SSLAnalysisResult['ssl_grade'] {
    if (result.ssl_status === 'no_ssl' || result.ssl_status === 'connection_error') {
      return 'F';
    }
    
    if (result.ssl_status === 'expired' || result.ssl_status === 'verify_failed') {
      return 'F';
    }
    
    if (result.ssl_status === 'self_signed') {
      return 'D';
    }

    let grade: SSLAnalysisResult['ssl_grade'] = 'A';

    // 인증서 만료 임박 체크
    if (result.days_until_expiry && result.days_until_expiry < CERTIFICATE_THRESHOLDS.warning_expiry_days) {
      grade = 'B';
    }

    // 보안 헤더 누락 체크
    const missingCriticalHeaders = result.missing_security_headers.filter(header =>
      ['Strict-Transport-Security', 'Content-Security-Policy', 'X-Frame-Options'].includes(header)
    ).length;

    if (missingCriticalHeaders >= 3) {
      grade = 'C';
    } else if (missingCriticalHeaders >= 2) {
      grade = 'B';
    } else if (missingCriticalHeaders >= 1) {
      if (grade === 'A') grade = 'B';
    }

    // HSTS 미설정 시 등급 하향
    if (!result.hsts_enabled && grade === 'A') {
      grade = 'A';
    }

    // 모든 보안 헤더가 설정되고 인증서가 완벽할 때만 A+
    if (grade === 'A' && result.missing_security_headers.length === 0 && result.hsts_enabled) {
      grade = 'A+';
    }

    return grade;
  }
}