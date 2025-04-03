import os
from tools.pdf_tool import PDFTool

def test_final_report_pdf():
    """
    펀드매니저 최종 리포트를 PDF로 생성하는 테스트
    """
    final_report_data = {
        "166090": {"final_decision": True, "reason": "LLM 결과: 찬성, 투자 타당성이 높음."},
        "001040": {"final_decision": False, "reason": "LLM 결과: 반대, 시장 변동성이 큼."}
    }
    filename = "test_final_report.pdf"
    
    pdf_tool = PDFTool()
    generated_file = pdf_tool.run(report_data=final_report_data,
                                  filename=filename,
                                  report_type="final")
    
    assert os.path.exists(generated_file), f"파일 생성 실패: {generated_file}"
    print(f"✅ 펀드매니저 최종 리포트 PDF 생성 성공: {generated_file}")


def test_critic_report_pdf():
    """
    Critic-Agent 리포트를 PDF로 생성하는 테스트
    """
    critic_report_md = """
# Critic Report
종목코드: 166090

## Analyst Report
CJ의 3분기 실적은 기대치를 하회했으며, 주요 자회사들의 실적 부진이 원인입니다.

## Critic Feedback
일부 내용에 모호함이 있습니다. 수정이 필요합니다.

## Revised Analysis
수정된 분석 내용: CJ의 실적 부진 원인은 주요 자회사의 영업이익 감소와 관련이 있습니다.
"""
    filename = "test_critic_report.pdf"
    
    pdf_tool = PDFTool()
    generated_file = pdf_tool.run(report_data=critic_report_md,
                                  filename=filename,
                                  report_type="critic")
    
    assert os.path.exists(generated_file), f"파일 생성 실패: {generated_file}"
    print(f"✅ Critic-Agent 리포트 PDF 생성 성공: {generated_file}")


if __name__ == "__main__":
    # 펀드매니저 최종 리포트 테스트 실행
    test_final_report_pdf()
    
    # Critic-Agent 리포트 테스트 실행
    test_critic_report_pdf()
