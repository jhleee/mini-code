"""
Static Checker Node - Code-Then-Execute Pattern (Phase 3)

정적 분석 게이트: 문법 및 린트 검사 통과 시에만 실행
실패 시 code_writer로 롤백하여 재생성

Pattern: Code-Then-Execute (⭐⭐⭐⭐)
- Prevents execution of invalid code
- Early error detection
- Faster feedback loop
"""
from typing import Dict, Any
from graph.state import AgentState, FeedbackResult, LintError, RetryContext
from graph.nodes.analyzer import StaticAnalyzer


class StaticChecker:
    """
    정적 분석 게이트 노드

    Workflow:
    1. 생성된 코드를 정적 분석 (syntax + lint)
    2. 통과 → execute 노드로 진행
    3. 실패 → feedback 저장, code_writer로 롤백

    Benefits:
    - 실행 전 에러 검출 (빠른 피드백)
    - 잘못된 코드 실행 방지
    - 재시도 횟수 절약
    """

    def __init__(self):
        self.analyzer = StaticAnalyzer()

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """정적 분석 게이트 실행"""

        current_idx = state.get("current_task_idx", 0)
        tasks = state.get("tasks", [])
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)

        if current_idx >= len(tasks):
            return {"status": "no_more_tasks"}

        current_task = tasks[current_idx]
        file_map = state.get("file_map", {})
        target_file = current_task.target_file

        # Get current file content
        if target_file not in file_map:
            print(f"[STATIC_CHECKER] ERROR: Target file {target_file} not in file_map")
            return {
                "status": "static_check_failed",
                "feedback": FeedbackResult(
                    passed=False,
                    syntax_errors=["Target file not found in file_map"],
                    lint_errors=[],
                    type_errors=[],
                    test_results=[]
                )
            }

        file_state = file_map[target_file]
        code = file_state.content

        if not code:
            print(f"[STATIC_CHECKER] Warning: Empty code for {target_file}, skipping check")
            return {"status": "static_check_passed"}

        print(f"[STATIC_CHECKER] Analyzing {target_file} ({len(code)} chars)...")

        # Run static analysis
        analysis = self.analyzer.analyze(code, target_file)

        # Check results
        syntax_valid = analysis["syntax_valid"]
        lint_passed = analysis["lint_passed"]

        print(f"[STATIC_CHECKER] Results:")
        print(f"  - Syntax: {'✓' if syntax_valid else '✗'}")
        print(f"  - Lint: {'✓' if lint_passed else '✗'} ({len(analysis['lint_errors'])} issues)")

        if analysis["syntax_errors"]:
            for error in analysis["syntax_errors"]:
                print(f"    [SYNTAX] {error}")

        if analysis["lint_errors"]:
            for error in analysis["lint_errors"]:
                print(f"    [{error.severity.upper()}] {error.code}: {error.message}")

        # Decide: pass or fail
        if syntax_valid and lint_passed:
            print(f"[STATIC_CHECKER] ✓ Static analysis passed, proceeding to execution")
            return {
                "status": "static_check_passed",
                "feedback": FeedbackResult(
                    passed=True,
                    syntax_errors=[],
                    lint_errors=analysis["lint_errors"],  # Keep warnings
                    type_errors=analysis["type_errors"],
                    test_results=[]
                )
            }
        else:
            # Failed: check retry limit
            if retry_count >= max_retries:
                print(f"[STATIC_CHECKER] ✗ Max retries ({max_retries}) reached, skipping to next task")
                return {
                    "status": "static_check_passed",  # Pass to avoid infinite loop
                    "current_task_idx": current_idx + 1,
                    "retry_count": 0,
                    "feedback": FeedbackResult(
                        passed=False,
                        syntax_errors=analysis["syntax_errors"],
                        lint_errors=analysis["lint_errors"],
                        type_errors=analysis["type_errors"],
                        test_results=[]
                    )
                }

            # Rollback failed code
            print(f"[STATIC_CHECKER] ✗ Static analysis failed, rolling back code (retry {retry_count + 1}/{max_retries})")

            generated_code = state.get("generated_code", "")
            if generated_code and file_state.content.endswith(generated_code):
                file_state.content = file_state.content[:-len(generated_code)].rstrip()
                print(f"[STATIC_CHECKER] Rolled back {len(generated_code)} chars from {target_file}")

            feedback = FeedbackResult(
                passed=False,
                syntax_errors=analysis["syntax_errors"],
                lint_errors=analysis["lint_errors"],
                type_errors=analysis["type_errors"],
                test_results=[]
            )

            # Create RetryContext for static check failure (Phase 3)
            error_type = "syntax" if not syntax_valid else "lint"
            error_details = (
                "\n".join(analysis["syntax_errors"])
                if not syntax_valid
                else "\n".join([f"Line {e.line}: [{e.code}] {e.message}" for e in analysis["lint_errors"][:5]])
            )

            previous_context = state.get("retry_context")
            previous_errors = []
            if previous_context and previous_context.error_details:
                previous_errors = previous_context.previous_errors + [previous_context.error_details]
                previous_errors = previous_errors[-3:]  # Keep last 3

            retry_context = RetryContext(
                error_type="static_check",
                failed_code=generated_code,
                error_details=f"[{error_type.upper()}]\n{error_details}",
                attempt=retry_count + 1,
                max_attempts=max_retries,
                previous_errors=previous_errors
            )

            print(f"[STATIC_CHECKER] Created RetryContext: {error_type} error")

            return {
                "status": "static_check_failed",
                "feedback": feedback,
                "file_map": file_map,
                "retry_count": retry_count + 1,
                "retry_context": retry_context
            }
