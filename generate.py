import os
import re
import subprocess
from collections import defaultdict

def find_imports_in_file(file_path):
    imports = set()
    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            content = file.read()
            # 표준 import 문 찾기
            import_lines = re.findall(r'^import\s+([\w\.,\s]+)', content, re.MULTILINE)
            for line in import_lines:
                for module in line.split(','):
                    base_module = module.strip().split('.')[0].split(' as ')[0]
                    if base_module and base_module != 'os' and base_module != 'sys' and base_module != 're':
                        imports.add(base_module)
            
            # from import 문 찾기
            from_imports = re.findall(r'^from\s+([\w\.]+)\s+import', content, re.MULTILINE)
            for module in from_imports:
                base_module = module.split('.')[0]
                if base_module and base_module != 'os' and base_module != 'sys' and base_module != 're':
                    imports.add(base_module)
        except UnicodeDecodeError:
            print(f"파일을 읽을 수 없습니다: {file_path}")
    
    return imports

def get_installed_packages():
    result = subprocess.run(['pip', 'list', '--format=freeze'], capture_output=True, text=True)
    installed_packages = {}
    
    for line in result.stdout.split('\n'):
        if '==' in line:
            package_name, version = line.split('==')
            installed_packages[package_name.lower()] = version
    
    return installed_packages

def main():
    all_imports = defaultdict(int)
    
    # 현재 디렉토리에서 모든 .py 파일 찾기
    for root, _, files in os.walk('.'):
        for file in files:
            if file.endswith('.py') and file != 'generate_requirements.py':
                file_path = os.path.join(root, file)
                imports = find_imports_in_file(file_path)
                for imp in imports:
                    all_imports[imp] += 1
    
    # pip로 설치된 패키지 가져오기
    installed_packages = get_installed_packages()
    
    # requirements.txt 파일 생성
    with open('requirements.txt', 'w') as req_file:
        for package_name in sorted(all_imports.keys()):
            package_lower = package_name.lower()
            if package_lower in installed_packages:
                req_file.write(f"{package_name}=={installed_packages[package_lower]}\n")
            else:
                req_file.write(f"{package_name}\n")
    
    print(f"requirements.txt 파일이 생성되었습니다. 총 {len(all_imports)}개의 패키지가 발견되었습니다.")
    print("참고: 패키지 이름이 임포트 이름과 다른 경우가 있으므로 파일을 확인하세요.")

if __name__ == "__main__":
    main()