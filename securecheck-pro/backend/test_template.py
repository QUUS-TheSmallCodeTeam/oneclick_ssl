#!/usr/bin/env python3

"""
TSC 템플릿 직접 테스트 스크립트
"""

from report_generator_tsc import _generate_tsc_html_report
from datetime import datetime

# 테스트 데이터
test_data = {
    'domain': 'example.com',
    'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'ssl_grade': 'F',
    'certificate_valid': False,
    'days_until_expiry': 0,
    'missing_headers': ['X-Frame-Options', 'X-Content-Type-Options', 'Strict-Transport-Security'],
    'annual_revenue_loss': 50000000,
    'server_info': {'software': 'nginx'},
    'redirects_https': False,
    'response_headers': {}
}

try:
    print("🧪 TSC 템플릿 테스트 시작...")
    html_content = _generate_tsc_html_report(test_data)
    
    # HTML 파일로 저장
    output_path = '/tmp/tsc_template_direct_test.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 테스트 성공! HTML 파일 저장됨: {output_path}")
    print(f"📝 HTML 길이: {len(html_content)} 문자")
    
except Exception as e:
    print(f"❌ 테스트 실패: {e}")
    import traceback
    traceback.print_exc()