# tools/pdf_tool.py
import os
import re
import html
import markdown2
from typing import Dict, Union
from fpdf import FPDF
from pyhtml2pdf import converter
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

class PDF(FPDF):
    pass

class PDFTool:
    """
    PDFTool은 두 가지 유형의 리포트를 생성합니다.
    
    1. 펀드매니저 최종 리포트 (report_type="final")
       - report_data는 { 종목코드: { 'final_decision': bool, 'reason': str, ... }, ... } 형태로 전달됩니다.
       - FPDF를 사용하여 PDF를 생성합니다.
       
    2. Critic-Agent 교환 리포트 (report_type="critic")
       - report_data는 마크다운 텍스트 또는 { 종목코드: { 'analysis': str, 'critic': str, 'revised_analysis': str, ... } } 형태로 전달됩니다.
       - 마크다운 텍스트를 HTML로 변환한 후, Selenium과 pyhtml2pdf를 사용해 PDF로 출력합니다.
    """
    def __init__(self):
        # 개인 폰트 경로 설정
        self.font_path = "/Users/daniel/Library/Fonts/NanumGothic-Regular.ttf"
        if not os.path.exists(self.font_path):
            raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {self.font_path}")

    def run(self, report_data: Union[Dict, str], filename: str = "final_report.pdf", report_type: str = "final") -> str:
        if report_type == "final":
            return self._generate_final_pdf(report_data, filename)
        elif report_type == "critic":
            return self._generate_critic_pdf(report_data, filename)
        else:
            raise ValueError(f"지원하지 않는 report_type입니다: {report_type}")

    def _generate_final_pdf(self, report_data: Union[Dict, str], filename: str) -> str:
        pdf = PDF()
        pdf.add_page()
        pdf.add_font("NanumGothic", "", self.font_path, uni=True)
        pdf.set_font("NanumGothic", size=12)
        pdf.cell(200, 10, txt="Final Fund Report", ln=1, align='C')
        if isinstance(report_data, dict):
            for ticker, data in report_data.items():
                pdf.cell(200, 10, txt=f"종목코드: {ticker}", ln=1)
                decision = data.get("final_decision", False)
                pdf.cell(200, 10, txt=f"편입여부: {'편입' if decision else '비편입'}", ln=1)
                pdf.multi_cell(0, 10, txt=f"사유: {data.get('reason', '')}")
                pdf.ln(5)
        else:
            pdf.multi_cell(0, 10, txt=str(report_data))
        pdf.output(filename)
        return filename

    def _generate_critic_pdf(self, report_data: Union[Dict, str], filename: str) -> str:
        # report_data가 dict이면, 각 종목별 마크다운 텍스트로 합칩니다.
        if isinstance(report_data, dict):
            markdown_text = ""
            for ticker, data in report_data.items():
                markdown_text += f"# 종목코드: {ticker}\n\n"
                if "analysis" in data:
                    markdown_text += "### Analyst Report\n"
                    markdown_text += f"{data['analysis']}\n\n"
                if "critic" in data:
                    markdown_text += "### Critic Feedback\n"
                    markdown_text += f"{data['critic']}\n\n"
                if "revised_analysis" in data:
                    markdown_text += "### Revised Analysis\n"
                    markdown_text += f"{data['revised_analysis']}\n\n"
                markdown_text += "\n---\n\n"
        elif isinstance(report_data, str):
            markdown_text = html.unescape(report_data)
        else:
            markdown_text = str(report_data)

        # 제목(예: 종목명 및 코드) 추출 (존재하는 경우)
        title_match = re.search(r"#\s*(.+?)\s*\((\d+)\)\s*투자 보고서", markdown_text)
        if title_match:
            stock_name = title_match.group(1)
            stock_code = title_match.group(2)
            page_title = f"{stock_name} ({stock_code}) 투자 보고서"
        else:
            page_title = "투자 보고서"

        # CSS 스타일을 포함한 HTML 템플릿 생성
        html_template = f"""
                        <!DOCTYPE html>
                        <html lang="ko">
                        <head>
                            <meta charset="UTF-8">
                            <title>{page_title}</title>
                            <style>
                                @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic&display=swap');
                                @import url('https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap');
                                body, h1, h2, h3, h4, h5, h6, p, li {{
                                    font-family: 'Nanum Gothic', 'Noto Color Emoji', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', Arial, sans-serif;
                                }}
                                body {{
                                    margin: 20px;
                                    line-height: 1.6;
                                }}
                                h1, h2, h3, h4 {{
                                    color: #333;
                                }}
                                ul {{
                                    margin-left: 20px;
                                }}
                            </style>
                        </head>
                        <body>
                            {markdown2.markdown(markdown_text)}
                        </body>
                        </html>
                        """
        # HTML 파일로 저장
        html_file_path = "report.html"
        with open(html_file_path, "w", encoding="utf-8") as f:
            f.write(html_template)
        print(f"📂 HTML 파일 저장 완료: {html_file_path}")

        # HTML -> PDF 변환
        self._convert_html_to_pdf(html_file_path, filename)
        return filename

    def _convert_html_to_pdf(self, html_file_path: str, pdf_file_path: str):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        abs_html_path = os.path.abspath(html_file_path)
        driver.get(f'file://{abs_html_path}')
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("✅ 페이지 로딩 완료")
        except Exception as e:
            print(f"❌ 페이지 로딩 실패: {e}")
        finally:
            driver.quit()

        converter.convert(f'file://{abs_html_path}', pdf_file_path)
        print(f"📂 PDF 파일 저장 완료: {pdf_file_path}")

# ✅ 실행 코드 (if __name__ == "__main__")
if __name__ == "__main__":
    # 예시: report_type이 "critic"인 경우
    # report_data가 문자열(마크다운) 또는 dict 형태 모두 지원
    sample_markdown = """
# 하나머티리얼즈 (166090) 투자 보고서

## 1. 투자 판단
### 매수/매도 의견
**매수**

### 투자 시사점
- 하나머티리얼즈의 주가가 악재를 반영한 상태에서 업황 회복 시 반등 가능성이 있음.

## 2. 투자 판단 근거
### 🔍 1) 실적 지표
#### 장점
- 2025년 매출액 30% 이상 성장 예상.
#### 단점
- NAND 감산 기조에 따른 매출 성장 부진 우려.

## 📝 종합 의견
- 장기적으로 매수, 단기 변동성 주의.
"""
    # report_data를 문자열 또는 dict로 전달 가능
    pdf_tool = PDFTool()
    output_pdf = pdf_tool.run(sample_markdown, filename="critic_report.pdf", report_type="critic")
    print(f"최종 PDF 파일: {output_pdf}")
