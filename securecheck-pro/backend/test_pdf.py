from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from io import BytesIO
from typing import Dict, Any

def create_styled_pdf_report(analysis_data: Dict[str, Any]) -> bytes:
    """보안 분석 데이터를 간단한 PDF로 변환합니다."""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()

        story = []

        # 제목
        title = f"{analysis_data.get('domain', 'Unknown')} Security Report"
        story.append(Paragraph(title, styles['Heading1']))
        story.append(Spacer(1, 12))

        # 내용
        content = f"Analysis Date: {analysis_data.get('analysis_date', 'N/A')}\n"
        content += f"Security Grade: {analysis_data.get('security_grade', 'N/A')}\n"
        content += f"Score: {analysis_data.get('security_score', 0)}/100\n\n"

        content += "Business Impact:\n"
        content += f"- User Loss Rate: {analysis_data.get('user_loss_rate', 0)}%\n"
        content += f"- Annual Loss: ${analysis_data.get('annual_loss', 0):,}\n"

        story.append(Paragraph(content, styles['Normal']))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        print(f"PDF 생성 중 오류: {str(e)}")
        # 오류 발생 시 아주 기본적인 PDF 생성
        return create_basic_pdf()

def create_basic_pdf() -> bytes:
    """기본적인 PDF를 생성합니다."""
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    # 아주 기본적인 텍스트
    c.drawString(100, 750, "Security Analysis Report")
    c.drawString(100, 700, "Basic PDF Generation Test")

    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# 테스트 데이터
test_data = {
    'domain': 'example.com',
    'analysis_date': '2024-01-15 14:30:25',
    'security_grade': 'B',
    'security_score': 75,
    'alert_message': '보안 검토가 필요합니다.',
    'user_loss_rate': 25.5,
    'annual_loss': 250000000,
    'seo_impact': 15,
    'trust_damage': 30,
    'conclusion_summary': '보안 강화를 권장합니다.'
}

if __name__ == "__main__":
    try:
        pdf_bytes = create_styled_pdf_report(test_data)
        print(f'실제 코드와 동일한 PDF 생성 성공: {len(pdf_bytes)} bytes')

        with open('test_actual.pdf', 'wb') as f:
            f.write(pdf_bytes)
        print('test_actual.pdf 생성됨')

    except Exception as e:
        print(f'실제 코드 테스트 오류: {str(e)}')
        import traceback
        traceback.print_exc()
