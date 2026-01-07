# Coding Agent

> **TL;DR**: PRD를 받아 Python 코드를 자동 생성하는 LangGraph 기반 에이전트. 파일 중심 아키텍처 + 세션 격리.

---

## Quick Reference

### File Map

| File | Purpose | When to Modify |
|------|---------|----------------|
| `main.py` | CLI 엔트리 포인트 | CLI 옵션 추가 시 |
| `graph/state.py` | 상태 스키마 정의 | 새 상태 필드 추가 시 |
| `graph/build_graph.py` | 노드 연결/라우팅 | 워크플로우 변경 시 |
| `graph/workspace_manager.py` | 세션/워크스페이스 관리 | 세션 로직 변경 시 |
| `graph/nodes/planner.py` | PRD → 파일구조 + 태스크 | 계획 로직 변경 시 |
| `graph/nodes/retriever.py` | 컨텍스트 검색 | 컨텍스트 전략 변경 시 |
| `graph/nodes/code_writer.py` | 코드 생성 | 코드 생성 로직 변경 시 |
| `graph/nodes/file_builder.py` | 파일 누적 (메모리) | 누적 로직 변경 시 |
| `graph/nodes/executor.py` | 코드 실행/테스트 + FeedbackResult | 실행 로직 변경 시 |
| `graph/nodes/analyzer.py` | 정적 분석 (syntax/lint/type) | 분석 로직 변경 시 |
| `graph/nodes/critic.py` | 평가/재시도 결정 | 재시도 전략 변경 시 |
| `graph/nodes/test_generator.py` | 테스트 자동 생성 | 테스트 생성 변경 시 |
| `graph/nodes/repo_manager.py` | 디스크 저장 | 저장 로직 변경 시 |

### Workflow

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

---

## Decision Tree

### 무엇을 수정해야 하나요?

```
새 기능 추가?
├─ 새 상태 필드 필요 → graph/state.py 수정 → main.py 초기값 추가
├─ 새 노드 필요 → graph/nodes/에 파일 생성 → build_graph.py에 연결
└─ 기존 노드 로직 변경 → 해당 노드 파일 수정

버그 수정?
├─ LLM JSON 파싱 에러 → planner.py의 정규표현식 확인
├─ 파일 저장 에러 → repo_manager.py 인코딩 확인 (utf-8)
├─ 재시도 무한루프 → critic.py의 max_retries 확인
└─ 세션 충돌 → workspace_manager.py 확인

테스트 관련?
├─ 테스트 생성 → test_generator.py
└─ 테스트 실행 → executor.py
```

---

## Core Concepts

### 1. 파일 중심 아키텍처

> **핵심**: 태스크별 파일이 아닌, 파일별로 코드 누적

```
# Bad (태스크 중심)          # Good (파일 중심)
task_0_add.py               calculator.py  ← 모든 함수
task_1_subtract.py          test_calculator.py
task_2_multiply.py
...
```

**이유**: Aider, Cursor, Devin 모두 파일 단위 작업

### 2. 워크스페이스 격리

> **핵심**: 세션별 독립 디렉토리로 동시 실행 지원

```
workspaces/
├─ sessions.json                  # 세션 레지스트리
├─ calculator_20260106_235521/    # Session 1
└─ todo_app_20260106_235622/      # Session 2
```

### 3. 상태 흐름

```
file_map: {} → {"calc.py": FileState} → {"calc.py": FileState(content="...")}
                ↑ Planner                 ↑ FileBuilder (누적)
```

**핵심 상태 필드**:
- `file_map`: Dict[str, FileState] - 파일별 코드 저장소
- `tasks`: List[Task] - 실행할 태스크 목록
- `current_task_idx`: int - 현재 태스크 인덱스
- `retry_count`: int - 현재 태스크 재시도 횟수

---

## CLI Commands

```bash
# 새 세션
python main.py run data/prds/calculator.md
python main.py run data/prds/calculator.md --session-id my_v1

# 세션 조회
python main.py list
python main.py list --prd calculator

# 세션 재개
python main.py run data/prds/calculator.md --resume

# 세션 정리
python main.py cleanup --days 7
```

---

## Common Tasks

### 새 노드 추가

1. `graph/nodes/my_node.py`:
```python
class MyNode:
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        return {"status": "my_node_done", "result": ...}
```

2. `graph/build_graph.py`:
```python
graph.add_node("my_node", MyNode())
graph.add_edge("prev_node", "my_node")
```

### 새 상태 필드 추가

1. `graph/state.py`: AgentState에 필드 추가
2. `main.py`: initial_state에 초기값 추가

---

## Known Issues & Fixes

| 증상 | 원인 | 해결 |
|------|------|------|
| `UnicodeEncodeError` | cp949 인코딩 | `encoding='utf-8'` 명시 |
| JSON 파싱 실패 | LLM 잘못된 JSON | planner.py 정규표현식 정리 |
| 파일명 에러 | 특수문자 포함 | `sanitize_filename()` 사용 |
| 무한 재시도 | retry 로직 버그 | `max_retries` 확인 |

---

## Constraints

- **Windows**: 절대 경로 사용, `encoding='utf-8'` 필수
- **LangGraph**: `recursion_limit=100` 설정 필요
- **파일 저장**: Save 노드에서만 디스크 I/O (메모리 누적 후)
- **테스트**: executor.py에서 각 테스트 독립 실행

---

## Debug

```bash
# 세션 상태 확인
cat workspaces/sessions.json

# 워크스페이스 확인
ls workspaces/calculator_20260106_*/
```

노드별 로깅: 각 노드에서 `print(f"[NODE] {state}")` 추가

---

## Architecture Rationale

<details>
<summary>왜 파일 중심인가?</summary>

- 상용 에이전트(Aider, Cursor, Devin) 패턴 분석 결과
- 파일 수 75% 감소
- 실제 개발 워크플로우와 일치
- 코드 응집도 향상
</details>

<details>
<summary>왜 세션 격리인가?</summary>

- 동시에 여러 PRD 처리 시 파일 충돌 방지
- 이전 세션 결과 보존
- 디버깅 용이
</details>

<details>
<summary>재시도 메커니즘</summary>

```
테스트 통과 → current_task_idx++ → 다음 태스크
테스트 실패 → retry_count < max? → 롤백 후 재시도
                         └─ max 초과 → 스킵 후 다음 태스크
```
</details>

---

## Agentic Patterns (from awesome-agentic-patterns)

### ✅ Phase 1-2 완료

#### Structured Output (⭐⭐⭐⭐⭐)
- `planner.py`: `llm.with_structured_output(PlannerOutput)` 적용
- `code_writer.py`: `llm.with_structured_output(CodeWriterOutput)` 적용
- Fallback: 파싱 실패 시 regex 기반 파싱으로 전환
- **Known Issue**: LLM structured output에서 newline 이스케이프 문제 발생 → `_validate_syntax()` 체크 후 fallback

#### Rich Feedback Loops (⭐⭐⭐⭐⭐)
- `analyzer.py`: 신규 생성 (StaticAnalyzer 클래스)
  - Syntax check: `ast.parse()`
  - Lint: `ruff --output-format=json` (미설치 시 graceful skip)
  - Type check: `mypy --output=json` (미설치 시 graceful skip)
- `executor.py`: FeedbackResult 통합, 개별 테스트 결과 수집
- `critic.py`: feedback 필드 사용, 에러 타입별 로깅
- `state.py`: LintError, TestResult, FeedbackResult 모델 추가

### 🔲 Phase 3-7 미구현

#### Code-Then-Execute (⭐⭐⭐⭐)
정적 분석 통과 시에만 실행하는 게이트 노드

```python
# 구현 계획
# graph/nodes/static_checker.py
class StaticChecker:
    """실행 전 정적 분석 게이트"""
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        # syntax + lint 통과해야 executor로 진행
        # 실패 시 code_writer로 롤백
```

수정 필요:
- `graph/nodes/static_checker.py` 생성
- `graph/build_graph.py`: write → static_check → execute 연결

#### Reflection Loop 개선 (⭐⭐⭐⭐)
에러 타입별 재시도 전략 차별화

```python
# 구현 계획
# graph/state.py
class RetryContext(BaseModel):
    error_type: Literal["syntax", "lint", "type", "test", "runtime"]
    failed_code: str
    error_details: str
    attempt: int

# graph/nodes/code_writer.py
# RetryContext 기반 프롬프트 차별화
# - syntax: "Fix syntax error at line X"
# - lint: "Fix lint error: {code} {message}"
# - test: "Test {name} failed: {error_message}"
```

수정 필요:
- `graph/state.py`: RetryContext 모델 추가
- `graph/nodes/code_writer.py`: 에러 타입별 프롬프트 템플릿
- `graph/nodes/critic.py`: RetryContext 생성 로직

#### Filesystem Checkpoint (⭐⭐⭐⭐)
태스크별 상태 저장/복구

```python
# 구현 계획
# graph/checkpoint_manager.py
class CheckpointManager:
    def save_checkpoint(self, state: AgentState, task_idx: int):
        # workspace/checkpoints/task_{idx}.json
    def load_checkpoint(self, task_idx: int) -> AgentState:
        # 특정 태스크 시점으로 복구
```

수정 필요:
- `graph/checkpoint_manager.py` 생성
- `graph/nodes/critic.py`: 태스크 완료 시 체크포인트 저장
- `main.py`: `--from-checkpoint N` 옵션 추가

#### Progressive Complexity (⭐⭐⭐)
간단한 태스크부터 처리

```python
# 구현 계획
# graph/nodes/task_sorter.py
class TaskSorter:
    def estimate_complexity(self, task: Task) -> int:
        # 키워드 기반 복잡도 추정
        # "create" < "append" < "modify"
        # 함수 수, import 수 등 휴리스틱
    def sort_tasks(self, tasks: List[Task]) -> List[Task]:
        # 복잡도 오름차순 정렬
```

수정 필요:
- `graph/nodes/task_sorter.py` 생성
- `graph/nodes/planner.py`: 태스크 정렬 적용

#### Anti-Reward-Hacking (⭐⭐⭐)
테스트 삭제/약화 감지

```python
# 구현 계획
# graph/nodes/test_guardian.py
class TestGuardian:
    def check_test_integrity(self, before: str, after: str) -> bool:
        # assert 문 개수 비교
        # 테스트 함수 수 비교
        # edge case 커버리지 체크
```

수정 필요:
- `graph/nodes/test_guardian.py` 생성
- `graph/nodes/code_writer.py`: 테스트 수정 시 guardian 체크

---

## Known Issues & Fixes

| 증상 | 원인 | 해결 |
|------|------|------|
| `UnicodeEncodeError` | cp949 인코딩 | `encoding='utf-8'` 명시 |
| JSON 파싱 실패 | LLM 잘못된 JSON | planner.py 정규표현식 정리 |
| 파일명 에러 | 특수문자 포함 | `sanitize_filename()` 사용 |
| 무한 재시도 | retry 로직 버그 | `max_retries` 확인 |
| Structured output 코드 잘림 | LLM newline 이스케이프 | `_validate_syntax()` 후 fallback |
| `dictionary changed size` | iteration 중 dict 수정 | 먼저 리스트로 수집 후 처리 |
| `Target file not in file_map` | Planner가 파일 생성 안함 | FileBuilder에서 자동 생성 |

---

## Future Work

- [ ] SEARCH/REPLACE 패턴 (현재 append만)
- [ ] 증분 실행 (`--from-task N`)
- [ ] 임베딩 기반 컨텍스트 검색
- [ ] 코드 리뷰 노드
