import json
from typing import Any, Dict
from .base_agent import BaseAgent

class CriticAgent(BaseAgent):
    """
    AnalystAgent가 작성한 리포트를 검토하여:
    - 내용의 타당성을 평가하고 오류나 모호한 부분을 지적하며,
    - 필요 시 '수정 요청을 해주세요'라는 문구를 포함한 피드백과 최종 매수/매도/보류 의견을
      **마크다운** 형식으로 요약한 리포트를 생성합니다.
    """

    def run(self, analyst_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        AnalystAgent의 리포트를 검토하고 결과를 반환합니다.

        :param analyst_report: AnalystAgent의 리포트 데이터 (종목코드: 리포트 내용)
        :return: 검토 결과 (critic, opinion, revise)
        """
        for ticker, report_text in analyst_report.items():
            print(f"\n[INFO] 📌 CriticAgent: 분석 시작 - 종목코드 = {ticker}")
            print(f"[DEBUG] 📄 애널리스트 리포트 내용:\n{report_text}")

            # 프롬프트 생성. AnalystAgent의 리포트 내용을 바탕으로 LLM에 전달할 프롬프트를 생성합니다.
            prompt = self._generate_prompt(report_text = report_text, information_extract=True)

            # LLM 호출
            critic_feedback = self._call_critic_llm(
                prompt=prompt
            )
            

            prompt = self._generate_prompt(report_text = report_text, information_extract=False, response=critic_feedback)
            critic_response = self._call_llm_structured(
                prompt=prompt,
                response_structure=self._get_response_format()
            )

            

            # 응답 파싱 및 오류 처리
            try:
                critic_response = json.loads(critic_response)
                critic_result = critic_response.get("critic", "")
                opinion = critic_response.get("opinion", False)
                revise = critic_response.get("revise", False)

            except json.JSONDecodeError as e:
                print(f"[ERROR] ❌ JSON 파싱 오류: {e}")
                critic_result = "파싱 오류로 인해 검토 결과를 생성할 수 없습니다."
                opinion = False
                revise = False

            results = {
                "critic": critic_feedback,
                "opinion": opinion,
                "revise": revise
            }

            print(f"#### 📝 CriticAgent 결과: {results}")

            return results

    def _generate_prompt(self, report_text: str, information_extract : bool, response :str = None) -> str:
        """
        LLM을 위한 프롬프트를 생성합니다.

        :param report_text: 애널리스트의 리포트 내용
        :return: 생성된 프롬프트 문자열
        """
        # response가 있는 경우, prompt를 다시 만들어 리포트 내용을 포함합니다.
        if response:
            prompt = f"""
            당신은 금융 애널리스트 보고서를 검토하는 뛰어난 Vice President 입니다.
            금융 애널리스트 보고서에 요구되는 필수적인 요소들에 대해 정확히 이해하고 있습니다.
            애널리스트의 리포트를 읽고 매수를 하고 싶은지 의견을 제시해보세요.
            
            아래의 보고서를 읽고, 이 보고서가 수정을 요청하는지, 매수 요청을 하는지 파악해야 합니다. 
            만약 수정을 요구한다면, revise = True로 설정하고, 아니라면 False로 설정해주세요. 
            
            만약 매수를 요구한다면, opinion = True로 설정하고, 아니라면 False로 설정해주세요.
            """
            
        else:
                
            prompt = f"""
            당신은 금융 애널리스트 보고서를 검토하는 뛰어난 Vice President 입니다.
            금융 애널리스트 보고서에 요구되는 필수적인 요소들에 대해 정확히 이해하고 있습니다.
            애널리스트가 작성한 리포트를 검토하여 다음과 같은 사항을 평가해 주세요.
            
            충분히 매력적이지 않다면 매수 요청을 제시하지 말아주세요.

            아래 조건을 엄격히 준수해 주세요:

            1. **보고서 타당성 평가**: 전체 내용을 읽고, 잘못된 정보나 모호한 부분이 있다면 구체적으로 지적해 주세요.
            2. **수정 요청**:
            - 보고서에 수정할 부분(오류, 추가 근거 필요 등)이 있다면, 최종 마크다운 보고서에
                반드시 `수정 요청을 해주세요` 문구를 포함해 주세요.
            - 수정이 필요 없다면, `수정 요청`이라는 단어를 절대 사용하지 마세요.
            3. **최종 매수/매도/보류 의견**:
            - 매수 의견을 주고 싶다면, 반드시 `매수 요청`이라는 단어를 포함해 주세요.
            - 매수 외의 의견(매도/보류)을 주고 싶다면, `매수 요청`이라는 단어가 절대 들어가지 않게 해주세요.
            4. 출력은 **마크다운** 형식으로 작성해 주세요.


     
            다음 애널리스트 보고서에 대한 피드백을 마크다운으로 작성하세요.

            ### 입력 리포트:
            {report_text}
            """
        return prompt

    def _get_response_format(self) -> Dict[str, Any]:
        """
        LLM 응답의 JSON 스키마를 정의합니다.

        :return: JSON 스키마 딕셔너리
        """
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "critic_response",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "critic": {
                            "type": "string",
                            "description": "리포트 피드백을 생성해줘요. 마크다운 형식으로 작성해 주세요."
                        },
                        "opinion": {
                            "type": "boolean",
                            "description": "매수 의견, True면 매수, False면 매도/보류"
                        },
                        "revise": {
                            "type": "boolean",
                            "description": "수정 요청 여부, True면 수정 요청, False면 수정 요청 없음"
                        }
                    }
                }
            }
        }
