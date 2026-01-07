# Coding Agent - Production-Ready File-Centric Implementation

LangGraph 기반 코딩 에이전트로, **상용 에이전트 패턴**을 따르며 **동시 실행**을 지원하는 프로덕션 레디 구현입니다.

PRD 문서를 입력하면 자동으로 Python 코드, 테스트, 문서를 생성합니다.

## 📦 설치 및 시작하기

### 의존성 설치
```bash
pip install langgraph langchain-openai pydantic

# 선택: 정적 분석 도구 (Rich Feedback)
pip install ruff mypy
```

### 빠른 시작
```bash
# 1. PRD 파일 준비 (예: data/prds/calculator.md)
# 2. 에이전트 실행
python main.py run data/prds/calculator.md

# 3. 결과 확인
ls workspaces/calculator_20260106_235521/
# calculator.py, test_calculator.py, SUMMARY.md
```

## 🚀 주요 기능

### ✅ 워크스페이스 격리

**동시 실행 지원**: 각 실행마다 독립적인 워크스페이스 생성

```bash
# Session 1: Calculator 구현
python main.py run data/prds/calculator.md &

# Session 2: Todo App 구현 (동시 실행!)
python main.py run data/prds/todo_app.md &

# 결과:
# workspaces/calculator_20260106_235521/
# workspaces/todo_app_20260106_235622/
```

### ✅ 파일 중심 아키텍처

**상용 패턴 준수**: 함수별 파일이 아닌 모듈별 파일 생성

```
workspaces/calculator_20260106_235521/
├── calculator.py        # 모든 함수가 하나의 파일에!
└── test_calculator.py   # 모든 테스트가 하나의 파일에!
```

**개선 효과**: 75% 파일 감소, Aider/Cursor/Devin 패턴 준수

## 📖 사용법

### 기본 실행
```bash
# PRD로 새 프로젝트 시작
python main.py run data/prds/calculator.md

# 자동 생성되는 세션 ID: calculator_20260106_235521
# 워크스페이스: workspaces/calculator_20260106_235521/
```

### 커스텀 세션 ID
```bash
# 의미있는 세션 이름 사용
python main.py run data/prds/calculator.md --session-id calc_v1_0
```

### 세션 관리
```bash
# 모든 세션 조회
python main.py list

# 특정 PRD의 세션만 조회
python main.py list --prd calculator

# 오래된 세션 정리 (7일 이상)
python main.py cleanup --days 7
```

## 📁 프로젝트 구조

```
.
├── main.py                    # 메인 실행 파일 (run/list/cleanup CLI)
├── graph/
│   ├── workspace_manager.py  # 세션 관리
│   ├── build_graph.py        # LangGraph 정의
│   ├── state.py              # State 스키마 (파일 중심)
│   └── nodes/
│       ├── planner.py        # 파일 구조 계획 (Structured Output)
│       ├── retriever.py      # 컨텍스트 검색
│       ├── code_writer.py    # 코드 생성 (Structured Output)
│       ├── file_builder.py   # 파일 누적
│       ├── analyzer.py       # 정적 분석 (syntax/lint/type)
│       ├── executor.py       # 테스트 실행 + FeedbackResult
│       ├── critic.py         # 평가 및 재시도
│       ├── test_generator.py # 테스트 생성
│       └── repo_manager.py   # 파일 저장
├── data/prds/                # PRD 예제
├── workspaces/               # 세션별 워크스페이스
│   ├── sessions.json         # 세션 레지스트리
│   ├── calculator_20260106_235521/
│   └── todo_app_20260106_235622/
└── tests/                    # 유닛 테스트
```

## 🔧 아키텍처

### 워크플로우

```
┌─────────┐
│   PRD   │
└────┬────┘
     │
     v
┌─────────────────┐
│  Plan Files     │  → file_map: {calculator.py, test_calculator.py}
│  & Tasks        │  → tasks: [add, subtract, multiply, divide]
└────┬────────────┘
     │
     v
┌────────────────────────────┐
│  For each task:            │
│                            │
│  1. Retrieve Context       │ → 기존 파일 내용 읽기
│     ↓                      │
│  2. Generate Code (LLM)    │ → 새 함수 생성
│     ↓                      │
│  3. Append to File         │ → file_map에 누적
│     ↓                      │
│  4. Execute Test           │ → 임시 실행 및 검증
│     ↓                      │
│  5. Critic                 │ → Pass: 다음 태스크
│     ├─ Pass ──────────┐    │   Fail: 재시도 (최대 3회)
│     └─ Fail → Retry   │    │
└────────────────────────┼───┘
                         │
                         v
                   ┌──────────────┐
                   │ Test Gen     │ → 모든 함수 테스트
                   └──────┬───────┘
                          │
                          v
                   ┌──────────────┐
                   │ Save Files   │ → 워크스페이스에 저장
                   └──────────────┘
```

### 핵심 컴포넌트

#### 1. Workspace Manager
- 세션별 독립 워크스페이스 생성
- JSON 기반 세션 레지스트리
- 타임스탬프 자동 생성

#### 2. File-Centric Planner
- PRD → 파일 구조 먼저 계획
- 관련 함수를 같은 파일로 그룹화

#### 3. File Builder
- 각 태스크의 코드를 같은 파일에 누적
- 함수 추적 및 중복 방지

#### 4. Test Generator
- 모든 함수를 위한 포괄적 테스트 자동 생성

## 🎯 상용 에이전트 패턴 준수

| 패턴 | Aider | Cursor | Devin | SWE-agent | This Agent |
|------|-------|--------|-------|-----------|------------|
| 파일 단위 작업 | ✅ | ✅ | ✅ | ✅ | ✅ |
| In-place 편집 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 파일 구조 계획 | ✅ | ✅ | ✅ | - | ✅ |
| 동시 실행 격리 | - | ✅ | - | - | ✅ |
| 세션 관리 | - | - | ✅ | - | ✅ |

## 🧠 Agentic Patterns (from awesome-agentic-patterns)

### ✅ 구현 완료

#### Structured Output
LLM 출력을 Pydantic 모델로 강제하여 JSON 파싱 에러 제거

```python
# planner.py - PlannerOutput 스키마 강제
structured_llm = llm.with_structured_output(PlannerOutput)
result: PlannerOutput = await structured_llm.ainvoke(messages)

# code_writer.py - CodeWriterOutput 스키마 강제
structured_llm = llm.with_structured_output(CodeWriterOutput)
result: CodeWriterOutput = await structured_llm.ainvoke(messages)
```

- Fallback: 파싱 실패 시 regex 기반 파싱으로 자동 전환

#### Rich Feedback Loops
Syntax, Lint, Type 에러를 구조화된 형태로 수집

```python
# analyzer.py - 정적 분석
analyzer = StaticAnalyzer()
analysis = analyzer.analyze(code, filename)
# → syntax_valid, syntax_errors, lint_errors

# executor.py - FeedbackResult 반환
feedback = FeedbackResult(
    syntax_valid=True,
    lint_passed=True,
    lint_errors=[LintError(...)],
    tests_passed=False,
    test_results=[TestResult(name="test_add", passed=True), ...],
    overall_passed=False,
    summary="3/4 tests passed"
)
```

- `ruff` 통합: `pip install ruff` 후 자동 활성화
- `mypy` 통합: `pip install mypy` 후 자동 활성화
- 미설치 시 graceful skip

### 🔲 구현 예정

| 패턴 | 우선순위 | 설명 |
|------|----------|------|
| Code-Then-Execute | ⭐⭐⭐⭐ | 정적 분석 통과 후에만 실행 |
| Reflection Loop | ⭐⭐⭐⭐ | 에러 타입별 재시도 전략 |
| Filesystem Checkpoint | ⭐⭐⭐⭐ | 태스크별 상태 저장/복구 |
| Progressive Complexity | ⭐⭐⭐ | 간단한 태스크부터 처리 |
| Anti-Reward-Hacking | ⭐⭐⭐ | 테스트 삭제/약화 감지 |

자세한 구현 계획은 `CLAUDE.md` 참조

## 📊 성능

### 파일 효율성
- **기존**: 4 tasks → 8 files
- **현재**: 4 tasks → 2 files (75% 감소)

### 코드 품질
- ✅ Type hints
- ✅ Docstrings
- ✅ 포괄적 테스트 (happy path + edge cases)
- ✅ 에러 처리

## 🛠️ 설정

### LLM 엔드포인트
```bash
# 커스텀 엔드포인트 사용
python main.py run data/prds/calculator.md \
  --base-url https://api.openai.com/v1
```

### 환경 변수
```bash
export LLM_BASE_URL="https://your-endpoint/v1"
export LLM_API_KEY="your-api-key"
export LLM_MODEL="gpt-4o"
```

## 📝 PRD 작성 가이드

### 좋은 PRD 예시
```markdown
# Calculator Application

## Requirements
1. Add function: add(a: float, b: float) -> float
2. Subtract function: subtract(a: float, b: float) -> float
3. Multiply function: multiply(a: float, b: float) -> float
4. Divide function with zero check

## Technical Specs
- Language: Python
- Type hints required
- Comprehensive tests
- Error handling for divide by zero
```

### Tips
- ✅ 명확한 기능 명세
- ✅ 기술 요구사항 명시
- ✅ 함수 시그니처 제공
- ❌ 너무 모호한 설명
- ❌ 구현 세부사항 과도하게 지정

## 🧪 테스트

```bash
# 유닛 테스트 실행
python run_tests.py
```

## 📊 예제 출력

```bash
$ python main.py run data/prds/calculator.md

============================================================
Starting Coding Agent - Session: calculator_20260106_235521
============================================================

[PLANNER] Planning file structure...
[PLANNER] Files: 1, Tasks: 4

[TASK 1/4] Implementing add function → calculator.py
[CODE_WRITER] Generated 15 lines
[EXECUTOR] Test passed ✓

[TASK 2/4] Implementing subtract function → calculator.py
[CODE_WRITER] Generated 12 lines
[EXECUTOR] Test passed ✓

[TASK 3/4] Implementing multiply function → calculator.py
[CODE_WRITER] Generated 12 lines
[EXECUTOR] Test passed ✓

[TASK 4/4] Implementing divide function → calculator.py
[CODE_WRITER] Generated 18 lines
[EXECUTOR] Test passed ✓

[TEST_GEN] Generating comprehensive tests...
[REPO_MANAGER] Saving 2 files to workspace...

============================================================
Agent Execution Complete
============================================================

Status: complete

Generated 1 files:
  - calculator.py: 856 chars, 4 functions

Workspace location: workspaces/calculator_20260106_235521

Files saved:
  - workspaces/calculator_20260106_235521/calculator.py
  - workspaces/calculator_20260106_235521/test_calculator.py
  - workspaces/calculator_20260106_235521/SUMMARY.md
```

## 🔍 트러블슈팅

### LLM 연결 실패
```bash
# 엔드포인트 확인
curl https://82c2209d4a22.ngrok-free.app/v1/models

# 커스텀 엔드포인트 사용
python main.py run data/prds/calculator.md \
  --base-url https://api.openai.com/v1
```

### JSON 파싱 에러
- LLM이 잘못된 JSON을 반환할 수 있음
- 자동 정리 로직이 포함되어 있음 (`planner.py`)
- 지속되면 `max_retries` 값 조정

### 테스트 실패 시
```bash
# 생성된 코드 확인
cat workspaces/{session_id}/*.py

# 디버그 모드로 재실행
python main.py run data/prds/calculator.md --session-id debug_session
```

### 워크스페이스 정리
```bash
# 7일 이상 된 세션 삭제
python main.py cleanup --days 7

# 특정 세션 수동 삭제
rm -rf workspaces/calculator_20260106_235521
```

## 📚 추가 문서

- **CLAUDE.md**: 아키텍처 상세 설명 및 개발자 가이드
- **data/prds/**: PRD 예제 파일들

## 🤝 기여

이슈 및 PR 환영합니다!

## 📄 라이선스

MIT License
