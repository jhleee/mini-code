---
description: 새 LangGraph 노드 추가 가이드
allowed-tools: Read, Write, Edit, Glob
argument-hint: [node-name]
---

새 노드 `$1`를 추가하는 단계별 가이드입니다.

## 절차

### 1. 상태 스키마 확인
먼저 `graph/state.py`를 읽어 AgentState 구조를 파악합니다.

### 2. 노드 파일 생성
`graph/nodes/$1.py` 파일을 생성합니다:

```python
from typing import Dict, Any
from graph.state import AgentState

class $1Node:
    """$1 노드 - [목적 설명]"""

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        # TODO: 구현
        return {
            "status": "$1_complete"
        }
```

### 3. 그래프 연결
`graph/build_graph.py`에 노드 추가:

```python
from graph.nodes.$1 import $1Node

# 노드 추가
graph.add_node("$1", $1Node())

# 엣지 연결 (이전/다음 노드에 따라 수정)
graph.add_edge("previous_node", "$1")
graph.add_edge("$1", "next_node")
```

### 4. 필요시 상태 필드 추가
`graph/state.py`와 `main.py`의 initial_state 수정

사용자에게 각 단계를 안내하고, 필요한 파일을 생성/수정합니다.
