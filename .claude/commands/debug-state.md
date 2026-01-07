---
description: 세션의 상태 흐름 디버깅
allowed-tools: Bash, Read, Grep, Glob
argument-hint: [session-id]
---

세션 `$1`의 상태를 분석합니다.

## 분석 항목

### 1. 세션 정보 확인
```bash
python main.py list | grep -A 5 "$1"
```

### 2. 워크스페이스 확인
```bash
ls -la workspaces/$1/
```

### 3. 생성된 파일 분석
```bash
wc -l workspaces/$1/*.py
head -50 workspaces/$1/*.py
```

### 4. 테스트 결과 확인
```bash
cd workspaces/$1 && pytest -v 2>&1 || echo "테스트 실패 또는 없음"
```

### 5. SUMMARY.md 확인
```bash
cat workspaces/$1/SUMMARY.md 2>/dev/null || echo "SUMMARY 없음"
```

## 결과 보고

- 세션 상태 (완료/실패/진행중)
- 생성된 파일 수와 라인 수
- 테스트 통과율
- 발견된 이슈
