import yaml

def load_config(config_path: str = "config.yaml") -> dict:
    """
    config.yaml 파일을 불러와서 Python 딕셔너리로 반환합니다.
    """
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config
