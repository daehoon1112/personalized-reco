#!/usr/bin/env bash
# 로컬 툴체인 보장: JDK 25 + uv + Python 3.12 + Node 없으면 설치한다 (macOS/Homebrew 기준).
# make dev 앞단에서 호출되며, 단독 실행도 가능: make bootstrap
set -euo pipefail

need_brew() {
  if ! command -v brew >/dev/null 2>&1; then
    echo "✗ Homebrew가 없다. 먼저 설치할 것: https://brew.sh" >&2
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"' >&2
    exit 1
  fi
}

# 1) JDK 25 — Makefile이 /usr/libexec/java_home -v 25 로 찾으므로 Temurin cask로 설치
if /usr/libexec/java_home -v 25 >/dev/null 2>&1; then
  echo "  ✓ JDK 25: $(/usr/libexec/java_home -v 25)"
else
  echo "▸ JDK 25 없음 → Temurin 25 설치"
  need_brew
  brew install --cask temurin@25 || brew install --cask temurin
  echo "  ✓ JDK 25: $(/usr/libexec/java_home -v 25)"
fi

# 2) uv — Python 의존성/인터프리터 관리 도구
if command -v uv >/dev/null 2>&1; then
  echo "  ✓ uv: $(uv --version)"
else
  echo "▸ uv 없음 → 설치"
  need_brew
  brew install uv
  echo "  ✓ uv: $(uv --version)"
fi

# 3) Python 3.12 — uv가 관리하는 인터프리터로 설치 (시스템 파이썬 불필요)
if uv python find '>=3.12' >/dev/null 2>&1; then
  echo "  ✓ Python: $(uv python find '>=3.12')"
else
  echo "▸ Python 3.12 없음 → uv로 설치"
  uv python install 3.12
  echo "  ✓ Python: $(uv python find '>=3.12')"
fi

# 4) Node — 스토어프론트(apps/web, Vite) 빌드/개발 서버용
if command -v node >/dev/null 2>&1; then
  echo "  ✓ Node: $(node --version)"
else
  echo "▸ Node 없음 → 설치"
  need_brew
  brew install node
  echo "  ✓ Node: $(node --version)"
fi
