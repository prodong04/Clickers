# tools/base_tool.py
import abc
from typing import Any, Dict

class BaseTool(abc.ABC):
    """
    Tool들이 공통으로 가져야 할 메서드/속성을 정의한 추상 클래스.
    필요에 따라 LLM, 설정(config), 다른 tool 연동 등을 지원.
    """

    def __init__(
        self,
        name: str,
        model_name: str = "",
        tools: Dict[str, Any] = None,
        config: Dict[str, Any] = None
    ):
        """
        :param name: 툴 이름 (e.g., "PriceTool")
        :param model_name: (옵션) 사용할 모델명 (HuggingFace 등)
        :param tools: (옵션) 다른 tool 객체들을 모은 dict
        :param config: (옵션) 기타 설정 (API KEY, temperature 등)
        """
        self.name = name
        self.model_name = model_name
        self.tools = tools if tools is not None else {}
        self.config = config if config is not None else {}

        # LLM 사용이 필요한 경우(예: HuggingFace)
        self.llm = self._load_huggingface_model(model_name, self.config)

    def _load_huggingface_model(self, model_name: str, config: Dict[str, Any]):
        """
        필요하다면 실제 모델(예: HF Transformers)을 로딩.
        여기서는 간단히 None 리턴.
        """
        if model_name:
            # return pipeline(...)
            return f"[Mock Model Loaded: {model_name}]"
        return None

    @abc.abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """
        각 Tool이 수행해야 할 메인 로직을 구현하는 추상 메서드.
        반드시 하위 클래스에서 override해야 함.
        """
        pass

    def _call_llm(self, prompt: str) -> str:
        """
        (옵션) LLM에 프롬프트를 전달하고 결과를 받는 메서드.
        Tool에서 LLM을 활용해야 한다면 사용 가능.
        """
        if not self.llm:
            return f"[No LLM available] {prompt}"
        # 실제로는 self.llm(prompt) 또는 pipeline(prompt) 등 사용
        return f"[{self.name} LLM 응답] {prompt[:100]}..."
