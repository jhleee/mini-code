---
description: 특정 노드의 구현 및 연결 상태 점검
allowed-tools: Read, Grep, Glob
argument-hint: [node-name]
---

노드 `$1`의 구현과 그래프 연결 상태를 점검합니다.

## 점검 항목

### 1. 노드 구현 확인
```bash
# 노드 파일 찾기
find graph/nodes -name "*$1*" -o -name "*$(echo $1 | tr '-' '_')*"
```

노드 파일을 읽고 분석:
- 클래스 구조
- 입력으로 사용하는 상태 필드
- 반환하는 상태 필드
- 에러 핸들링

### 2. 그래프 연결 확인
```bash
# build_graph.py에서 노드 관련 코드 찾기
grep -n "$1" graph/build_graph.py
```

확인할 내용:
- 노드가 그래프에 추가되었는지
- 이전 노드에서 연결되는지
- 다음 노드로 연결되는지
- 조건부 라우팅이 있는지

### 3. 상태 의존성 분석
```bash
# 이 노드가 사용하는 상태 필드
grep -o 'state\["[^"]*"\]' graph/nodes/*$1*.py | sort -u
```

### 4. 호출 관계 확인
```bash
# 이 노드를 import하는 파일
grep -l "$1" graph/*.py
```

## 점검 결과 보고

- 노드 위치: `graph/nodes/...`
- 입력 상태: [필드 목록]
- 출력 상태: [필드 목록]
- 이전 노드: [노드명]
- 다음 노드: [노드명]
- 잠재적 이슈: [있으면 설명]
