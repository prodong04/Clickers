#!/bin/bash

# 쉘 스크립트 에러 발생 시 중단
set -e

ENV_NAME="clicker"
ENV_FILE="environment.yaml"

# 1. Conda 설치 확인
if ! command -v conda &> /dev/null; then
    echo "Conda가 설치되어 있지 않습니다. 설치를 진행합니다."
    if [ "$(uname)" == "Darwin" ]; then
        echo "MacOS에서 Conda 설치 중..."
        /bin/bash -c "$(curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh)"
    elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
        echo "Linux에서 Conda 설치 중..."
        wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
        bash miniconda.sh -b -p $HOME/miniconda
        rm miniconda.sh
        export PATH="$HOME/miniconda/bin:$PATH"
    else
        echo "지원하지 않는 운영체제입니다."
        exit 1
    fi
else
    echo "Conda가 이미 설치되어 있습니다."
fi

# 2. Conda 환경 생성 또는 업데이트
if conda env list | grep -q "$ENV_NAME"; then
    echo "Conda 환경 '$ENV_NAME'이 이미 존재합니다. 업데이트를 진행합니다."
    conda env update -f $ENV_FILE --prune
else
    echo "Conda 환경 '$ENV_NAME'을(를) 생성합니다."
    conda env create -f $ENV_FILE
fi

# 3. Conda 환경 활성화
echo "Conda 환경을 활성화합니다: $ENV_NAME"
source $(conda info --base)/etc/profile.d/conda.sh
conda activate $ENV_NAME

# 4. Homebrew 설치 확인 (MacOS 용)
if [ "$(uname)" == "Darwin" ]; then
    if ! command -v brew &> /dev/null; then
        echo "Homebrew가 설치되어 있지 않습니다. 설치를 진행합니다."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    echo "Homebrew Cask로 나눔고딕 폰트를 설치합니다."
    brew tap homebrew/cask-fonts
    brew install --cask font-nanum-gothic
fi

# 5. 설치 확인 메시지 출력
echo "환경 설정이 완료되었습니다. 다음 명령어로 환경을 활성화하세요:"
echo "conda activate $ENV_NAME"
