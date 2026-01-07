---
name: langgraph-patterns
description: LangGraph 패턴 및 이 Coding Agent 프로젝트의 아키텍처 지식. "LangGraph", "노드", "상태", "워크플로우" 관련 질문 시 자동 로드.
allowed-tools: Read, Grep, Glob
---

# LangGraph Patterns for Coding Agent

이 스킬은 LangGraph 패턴과 이 Coding Agent 프로젝트의 아키텍처 지식을 제공합니다.

## 프로젝트 아키텍처

### 핵심 개념

**파일 중심 아키텍처**: 태스크별 파일이 아닌, 파일별로 코드 누적
- `file_map: Dict[str, FileState]`가 중앙 저장소
- 각 태스크가 `file_map[target_file].content`에 코드 추가
- Save 노드에서 한 번에 디스크 저장

**워크스페이스 격리**: 세션별 독립 디렉토리
- `workspaces/{prd_name}_{timestamp}/`
- 동시 실행 지원

### 워크플로우

```
plan → retrieve → write → build → execute → critic ─┐
                                                     │
         ┌───────────────────────────────────────────┘
         ↓
    (retry or next task)
         │
         ↓ (all tasks done)
    test_gen → save → END
```

## LangGraph 패턴

### 노드 정의

```python
class MyNode:
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        # 상태 읽기
        data = state["field_name"]

        # 처리

        # 변경된 필드만 반환
        return {"updated_field": new_value}
```

### 조건부 라우팅

```python
def route_function(state: AgentState) -> str:
    if condition:
        return "node_a"
    return "node_b"

graph.add_conditional_edges(
    "source_node",
    route_function,
    {"node_a": "node_a", "node_b": "node_b"}
)
```

### 루프 패턴

```python
def should_continue(state: AgentState) -> str:
    if state["current_idx"] >= len(state["items"]):
        return "end"
    return "continue"

graph.add_conditional_edges("process", should_continue, {
    "continue": "process",
    "end": "finalize"
})
```

## 상태 스키마

### AgentState 필드

| 필드 | 타입 | 용도 |
|------|------|------|
| file_map | Dict[str, FileState] | 파일별 코드 저장 |
| tasks | List[Task] | 실행할 태스크 |
| current_task_idx | int | 현재 태스크 인덱스 |
| retry_count | int | 재시도 횟수 |
| status | str | 현재 상태 |
| context | str | 컨텍스트 정보 |
| generated_code | str | 생성된 코드 |
| exec_result | str | 실행 결과 |

### FileState 필드

| 필드 | 타입 | 용도 |
|------|------|------|
| path | str | 파일 경로 |
| purpose | str | 파일 목적 |
| content | str | 누적된 코드 |
| functions | List[str] | 포함된 함수 목록 |

## 주요 파일

- `graph/state.py`: 상태 스키마
- `graph/build_graph.py`: 그래프 구성
- `graph/nodes/*.py`: 노드 구현
- `graph/workspace_manager.py`: 세션 관리
- `main.py`: 엔트리 포인트

## 디버깅 팁

```bash
# 상태 필드 사용 현황
grep -oh "state\[\"[^\"]*\"\]" graph/nodes/*.py | sort | uniq -c

# 노드 반환값 확인
grep -A 3 "return {" graph/nodes/*.py

# 조건부 라우팅 확인
grep -B 5 -A 10 "add_conditional" graph/build_graph.py
```

## 제약 사항

- Windows: `encoding='utf-8'` 필수
- LangGraph: `recursion_limit=100` 설정
- JSON 파싱: 정규표현식으로 사전 정리 필요
