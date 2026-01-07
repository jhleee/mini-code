---
description: PRD 파일로 Coding Agent 실행
allowed-tools: Bash, Read, Glob
argument-hint: [prd-file]
---

PRD 파일 `$1`로 Coding Agent를 실행합니다.

## 실행 절차

1. PRD 파일 존재 확인
2. 에이전트 실행
3. 결과 요약

```bash
# PRD 파일 확인
ls data/prds/$1 2>/dev/null || ls data/prds/$1.md 2>/dev/null

# 에이전트 실행
python main.py run data/prds/$1
```

실행 후:
- 생성된 워크스페이스 경로 알려주기
- 생성된 파일 목록 보여주기
- 테스트 결과 요약하기
