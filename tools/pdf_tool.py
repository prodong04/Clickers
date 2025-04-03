# # tools/pdf_tool.py
# import os
# import re
# import html
# import markdown2
# from typing import Dict, Union

# class PDFTool:
#     """
#     PDFTool은 두 가지 유형의 리포트를 생성합니다.
    
#     1. Critic-Agent 교환 리포트 (report_type="critic")
#        - report_data는 마크다운 텍스트 또는 { 종목코드: { 'analysis': str, 'critic': str, 'revised_analysis': str, ... } } 형태로 전달됩니다.
#        - 마크다운 텍스트를 HTML로 변환하고 CSS 스타일을 적용하여 HTML 파일로 출력합니다.
#     """
#     def __init__(self):
#         pass

#     def run(self, report_data: Union[Dict, str], filename: str = "report.html", report_type: str = "critic") -> str:
#         # report_data가 dict이면, 각 종목별 마크다운 텍스트로 합칩니다.
#         if isinstance(report_data, dict):
#             markdown_text = ""
#             for ticker, data in report_data.items():
#                 markdown_text += f"# 종목코드: {ticker}\n\n"
#                 if "analysis" in data:
#                     markdown_text += f"### Analyst Report\n{data['analysis']}\n\n"
#                 if "critic" in data:
#                     markdown_text += f"### Critic Feedback\n{data['critic']}\n\n"
#                 if "revised_analysis" in data:
#                     markdown_text += f"### Revised Analysis\n{data['revised_analysis']}\n\n"
#                 markdown_text += "\n---\n\n"
#         elif isinstance(report_data, str):
#             markdown_text = html.unescape(report_data)
#         else:
#             markdown_text = str(report_data)

#         # 제목 설정
#         page_title = "투자 보고서"

#         # HTML 템플릿 (노션 스타일로 적용)
#         html_template = f"""
# <!DOCTYPE html>
# <html lang="ko">
# <head>
#     <meta charset="UTF-8">
#     <title>{page_title}</title>
#     <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css">
#     <style>
#         body {{
#             font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
#             background-color: #f5f5f5;
#             padding: 20px;
#             line-height: 1.6;
#         }}
#         .container {{
#             max-width: 800px;
#             margin: 0 auto;
#             background: white;
#             padding: 30px;
#             border-radius: 10px;
#             box-shadow: 0 2px 4px rgba(0,0,0,0.1);
#         }}
#         h1, h2, h3 {{
#             margin-top: 20px;
#             color: #2c3e50;
#         }}
#         p {{
#             color: #4d4d4d;
#         }}
#         ul, ol {{
#             margin-left: 20px;
#         }}
#         blockquote {{
#             border-left: 4px solid #dfe2e5;
#             padding-left: 16px;
#             color: #6a737d;
#             background-color: #f0f0f0;
#             border-radius: 4px;
#         }}
#         code {{
#             background-color: #f0f0f0;
#             padding: 2px 4px;
#             border-radius: 4px;
#         }}
#         hr {{
#             border: none;
#             border-top: 1px solid #dfe2e5;
#             margin: 20px 0;
#         }}
#     </style>
# </head>
# <body>
#     <div class="container">
#         {markdown2.markdown(markdown_text)}
#     </div>
# </body>
# </html>
# """

#         # HTML 파일로 저장
#         with open(filename, "w", encoding="utf-8") as f:
#             f.write(html_template)
#         print(f"📂 HTML 파일 저장 완료: {filename}")
#         return filename

# # ✅ 실행 코드 (if __name__ == "__main__")
# if __name__ == "__main__":
#     # 예시: report_type이 "critic"인 경우
# #     sample_markdown = """
# # # 하나머티리얼즈 (166090) 투자 보고서

# # ## 1. 투자 판단
# # ### 매수/매도 의견
# # **매수**

# # ### 투자 시사점
# # - 하나머티리얼즈의 주가가 악재를 반영한 상태에서 업황 회복 시 반등 가능성이 있음.

# # ## 2. 투자 판단 근거
# # ### 🔍 1) 실적 지표
# # #### 장점
# # - 2025년 매출액 30% 이상 성장 예상.
# # #### 단점
# # - NAND 감산 기조에 따른 매출 성장 부진 우려.

# # ## 📝 종합 의견
# # - 장기적으로 매수, 단기 변동성 주의.
# # """
#     sample_markdown = """
#                         # 하이트진로 (000080) AI 투자 보고서
#                     ## ✅ 매수/매도 의견
#                     - 💡 의견: 매수 (BUY)
#                     - 투자 기간: 12개월
#                     - 투자 전략: 중장기 보유 추천

#                     ## 💡 투자 시사점
#                     - 소주 시장 지배력 유지 및 증류주 판매 확대
#                     - 경쟁사 맥주 가격 인상으로 인한 수혜 가능성
#                     - 비용 효율성 개선과 브랜드 마케팅 강화

#                     ## 📊 장단점 기반 판단 근거
#                     ✅ 장점
#                     - 시장 점유율 유지 및 증류주 판매 증가
#                     - 광고선전비 축소로 비용 효율성 향상
#                     - '켈리', '테라' 브랜드 마케팅 성공

#                     ❌ 단점
#                     - 맥주 부문 실적 부진
#                     - 경기 침체로 주류 시장 성장 제한
#                     - 원가 상승 및 환율 변동 리스크

#                     ## 📈 종합 의견
#                     - 중장기 성장 가능성 높음, 단기 리스크 존재
#                     - 투자 권고: 공격적 투자자에게 적합

#                     ## 📊 리스크 대응 방안
#                     - 환율 변동 모니터링
#                     - 원가 절감 대책 마련"""
#     pdf_tool = PDFTool()
#     output_html = pdf_tool.run(sample_markdown, filename="critic_report.html", report_type="critic")
#     print(f"최종 HTML 파일: {output_html}")
# tools/pdf_tool.py
import os
import re
import html
import markdown2
from typing import Dict, Union

class PDFTool:
    """
    PDFTool은 두 가지 유형의 리포트를 생성합니다.
    
    1. Critic-Agent 교환 리포트 (report_type="critic")
       - report_data는 마크다운 텍스트 또는 { 종목코드: { 'analysis': str, 'critic': str, 'revised_analysis': str, ... } } 형태로 전달됩니다.
       - 마크다운 텍스트를 HTML로 변환하고 CSS 스타일을 적용하여 HTML 파일로 출력합니다.
    """
    def __init__(self):
        pass

    def clean_markdown_text(self, text):
        """마크다운 텍스트를 정리합니다: 불필요한 들여쓰기 제거"""
        lines = text.split("\n")
        # 불필요한 들여쓰기 제거
        cleaned_lines = []
        for line in lines:
            cleaned_lines.append(line.strip())
        return "\n".join(cleaned_lines)

    def run(self, report_data: Union[Dict, str], filename: str = "report.html", report_type: str = "critic") -> str:
        # report_data가 dict이면, 각 종목별 마크다운 텍스트로 합칩니다.
        if isinstance(report_data, dict):
            markdown_text = ""
            for ticker, data in report_data.items():
                markdown_text += f"# 종목코드: {ticker}\n\n"
                if "analysis" in data:
                    markdown_text += f"### Analyst Report\n{data['analysis']}\n\n"
                if "critic" in data:
                    markdown_text += f"### Critic Feedback\n{data['critic']}\n\n"
                if "revised_analysis" in data:
                    markdown_text += f"### Revised Analysis\n{data['revised_analysis']}\n\n"
                markdown_text += "\n---\n\n"
        elif isinstance(report_data, str):
            markdown_text = html.unescape(report_data)
        else:
            markdown_text = str(report_data)

        # 마크다운 텍스트 정리
        markdown_text = self.clean_markdown_text(markdown_text)
        
        # 디버깅용 출력
        print("변환 전 마크다운 텍스트:")
        print(markdown_text[:200] + "...")  # 처음 200자만 출력
        
        # 제목 설정
        page_title = "투자 보고서"

        # markdown2 확장 기능 활성화
        extras = [
            "fenced-code-blocks", 
            "tables", 
            "header-ids", 
            "break-on-newline", 
            "cuddled-lists",
            "markdown-in-html"
        ]
        
        # HTML로 변환
        html_content = markdown2.markdown(markdown_text, extras=extras)
        
        # HTML 템플릿 (노션 스타일로 적용)
        html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>{page_title}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1, h2, h3 {{
            margin-top: 20px;
            color: #2c3e50;
        }}
        p {{
            color: #4d4d4d;
        }}
        ul, ol {{
            margin-left: 20px;
        }}
        blockquote {{
            border-left: 4px solid #dfe2e5;
            padding-left: 16px;
            color: #6a737d;
            background-color: #f0f0f0;
            border-radius: 4px;
        }}
        code {{
            background-color: #f0f0f0;
            padding: 2px 4px;
            border-radius: 4px;
        }}
        hr {{
            border: none;
            border-top: 1px solid #dfe2e5;
            margin: 20px 0;
        }}
        /* 이모지 스타일 */
        .emoji {{
            font-family: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji";
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_content}
    </div>
</body>
</html>
"""

        # HTML 파일로 저장
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_template)
        print(f"📂 HTML 파일 저장 완료: {filename}")
        return filename

# ✅ 실행 코드 (if __name__ == "__main__")
if __name__ == "__main__":
    sample_markdown = """
# 하이트진로 (000080) AI 투자 보고서
## ✅ 매수/매도 의견
- 💡 의견: 매수 (BUY)
- 투자 기간: 12개월
- 투자 전략: 중장기 보유 추천

## 💡 투자 시사점
- 소주 시장 지배력 유지 및 증류주 판매 확대
- 경쟁사 맥주 가격 인상으로 인한 수혜 가능성
- 비용 효율성 개선과 브랜드 마케팅 강화

## 📊 장단점 기반 판단 근거
✅ 장점
- 시장 점유율 유지 및 증류주 판매 증가
- 광고선전비 축소로 비용 효율성 향상
- '켈리', '테라' 브랜드 마케팅 성공

❌ 단점
- 맥주 부문 실적 부진
- 경기 침체로 주류 시장 성장 제한
- 원가 상승 및 환율 변동 리스크

## 📈 종합 의견
- 중장기 성장 가능성 높음, 단기 리스크 존재
- 투자 권고: 공격적 투자자에게 적합

## 📊 리스크 대응 방안
- 환율 변동 모니터링
- 원가 절감 대책 마련
"""
    pdf_tool = PDFTool()
    output_html = pdf_tool.run(sample_markdown, filename="critic_report.html", report_type="critic")
    print(f"최종 HTML 파일: {output_html}")