import json
from typing import Any, Dict
from .base_agent import BaseAgent

class CriticAgent(BaseAgent):
    """
    AnalystAgent가 작성한 리포트를 검토하여,
    - 내용의 타당성을 평가하고 오류나 모호한 부분을 지적하며,
    - 필요 시 '수정'이라는 단어를 포함한 피드백과 최종 매수/매도/보류 의견을 요약한 **마크다운** 리포트를 생성합니다.
    """
    def run(self, analyst_report: Dict[str, Any]) -> Dict[str, Any]:

        for ticker, report_data in analyst_report.items():
            print(f"\n[INFO] 📌 CriticAgent: 분석 시작 - 종목코드 = {ticker}")
            analysis_text = report_data
            print(f"[DEBUG] 📄 애널리스트 리포트 내용:\n{analysis_text}")
            
            # Few-shot 예시를 포함한 프롬프트 예시
            prompt = f"""
            당신은 금융 애널리스트 보고서를 검토하는 역할입니다.

            아래 조건을 엄격히 준수해 주세요:

            1. **보고서 타당성 평가**: 전체 내용을 읽고, 잘못된 정보나 모호한 부분이 있다면 구체적으로 지적해 주세요.
            2. **수정 요청**:
            - 만약 보고서에 수정할 부분(오류, 추가적 근거 필요 등)이 있다면, 최종 마크다운 보고서 어딘가에 반드시 `수정 요청을 해주세요`라는 문구를 포함해 주세요.
            - 수정이 필요 없다면, 절대로 `수정 요청`이라는 단어 자체를 쓰지 마세요.
            3. **최종 매수/매도/보류 의견**:
            - 매수 의견을 주고 싶다면, 반드시 `매수 요청`이라는 단어를 포함해 주세요.
            - 매수 외에 매도/보류 등의 의견을 주고 싶다면, `매수 요청`이라는 단어가 절대 들어가지 않게 해주세요.
            4. 출력은 **마크다운** 형식으로 작성해 주세요.

            ---

            ## Few-shot Examples

            아래는 입력 리포트(분석 초안)와 최종 출력(검토 결과) 예시입니다.

            ### 예시 1
            **입력 리포트**:
            이 회사는 최근 3년간 꾸준한 흑자를 기록했으며, 미래 전망 역시 긍정적입니다. 
            하지만 매출 추이의 변동 요인에 대한 분석이 부족합니다. 
            그래도 내년 초에 신규 사업이 본격화되면 실적이 크게 오를 것으로 보입니다.

            markdown
            복사
            편집
            **출력(최종 보고서)**:
            종목 검토 결과
            회사의 과거 실적이 견조하다는 점은 긍정적입니다. 
            다만 매출 변동 요인 분석이 누락된 점이 있어 해당 부분을 보강하면 좋겠습니다. 수정 요청을 해주세요

            최종 의견
            **매수 요청**
            회사의 신규 사업 진출로 장기적 성장이 기대됩니다.

            > **해설**:  
            > - 매출 변동에 대한 추가 분석이 누락 → `수정 요청을 해주세요` 문구 포함  
            > - 매수 의견 → `매수 요청` 문구 포함  

            ---

            ### 예시 2
            **입력 리포트**:
            이 회사는 올해 큰 적자를 냈습니다. 일부 신사업이 실패하여 재무구조가 나빠졌습니다. 단기적으로 뚜렷한 반등 요인도 없어 보입니다.

            markdown
            복사
            편집
            **출력(최종 보고서)**:
            종목 검토 결과
            회사의 적자 폭이 크고, 재무구조 취약성이 단기간에 개선될 여지가 적어 보입니다. 현재 보고서 내용에 큰 오류나 추가 보완이 필요한 사항은 없어 보입니다.

            최종 의견
            매도/보류
            단기적인 투자 매력은 낮다고 판단됩니다.

            > **해설**:  
            > - 특별히 수정할 부분이 없으므로 `수정 요청을 해주세요` 문구 없음  
            > - 매도/보류 의견 → `매수 요청` 문구 없음  

            ---

            ### 예시 3
            **입력 리포트**:
            현재 원자재 가격 변동성에 대한 고려가 미흡합니다. 또한 매출 구조나 시장 점유율에 대한 데이터가 구체적으로 제시되지 않습니다. 향후 2년간 꾸준히 매출액이 성장할 것으로 기대됩니다.

            **출력(최종 보고서)**:
            종목 검토 결과
            시장 점유율, 원자재 가격 변동성 등에 대한 구체적 분석이 필요해 보입니다. 수정 요청을 해주세요

            최종 의견
            매도/보류
            매출 증대 가능성은 있으나, 필수 정보가 누락되어 있어 보류 의견을 제시합니다.


            > - 누락된 정보들이 많으므로 수정 필요 → `수정 요청을 해주세요` 문구 포함  
            > - 보류 의견 → `매수 요청` 문구 없음  

            ---

            ## 요청사항
            이제 다음 애널리스트 보고서를 바탕으로 위와 같은 형식에 맞춰 최종 보고서를 마크다운으로 작성하세요.  
            (조건: 타당성 평가, 수정 필요 시 `수정 요청을 해주세요`, 매수 시 `매수 요청`, 매수 외에는 `매수 요청` 금지)

            ### 입력 리포트:
            {analysis_text}

            """
            response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": "critic_response",
                                "strict": True,
                                "schema": {
                            "type" : "object",
                            "properties" : {
                                "critic" : {
                                    "type" : "string",
                                    "description" : "리포트 검토 결과"
                                },
                                "opinion" : {
                                    "type" : "boolean",
                                    "description" : "매수 의견, True면 매수, False면 매도/보류"
                                },
                                "revise" : {
                                    "type" : "boolean",
                                    "description" : "수정 요청 여부, True면 수정 요청, False면 수정 요청 없음"
                                }
                            }
                                }
                            }
                            }
            critic_response = self._call_llm_structured(prompt = prompt, response_structure=response_format)

            # 결과 파싱
            critic_response = json.loads(critic_response)
            critic_result = critic_response.get("critic", "")
            opinion = critic_response.get("opinion", False)
            revise = critic_response.get("revise", False)
            
            results = {
                "critic": critic_result,
                "opinion": opinion,  # 실제 구현에서는 critic_response 파싱 필요
                "revise": revise
            }

        print(f"#### 📝 CriticAgent 결과 : {results}")
        return results

