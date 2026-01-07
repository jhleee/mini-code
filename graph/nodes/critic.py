"""
Critic Node - 실행 결과 평가 및 재시도 결정

Phase 2: Rich Feedback Loops
- feedback 필드 사용 (FeedbackResult)
- 에러 타입별 상세 로깅
- 호환성을 위해 exec_result도 지원

Phase 3: Reflection Loop
- RetryContext 생성 (에러 타입별 차별화)
- 이전 에러 히스토리 추적
"""
from typing import Dict, Any, List, Optional
from graph.state import AgentState, FeedbackResult, RetryContext
from graph.checkpoint_manager import CheckpointManager


class Critic:
    """
    Critic with Rich Feedback (Phase 2)

    FeedbackResult를 사용하여 에러 타입별 상세 정보 로깅

    Phase 3: Checkpoint support
    Saves checkpoint on task completion
    """

    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = workspace_dir
        self.checkpoint_manager = CheckpointManager(workspace_dir) if workspace_dir else None

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Evaluate test results and update task status"""
        # feedback 우선, 없으면 exec_result 사용 (호환성)
        feedback: FeedbackResult = state.get("feedback")
        exec_result = state.get("exec_result")

        current_idx = state.get("current_task_idx", 0)
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        tasks = state.get("tasks", [])

        # Determine pass/fail
        if feedback:
            passed = feedback.overall_passed
        elif exec_result:
            passed = exec_result.passed
        else:
            print("[CRITIC] ERROR: No feedback or exec_result")
            return {
                "status": "error_no_result",
                "retry_count": retry_count + 1
            }

        if current_idx >= len(tasks):
            return {"status": "all_tasks_complete"}

        current_task = tasks[current_idx]

        if passed:
            # Success
            current_task.completed = True
            current_task.code_snippet = state.get("generated_code", "")

            print(f"[CRITIC] Task {current_idx} PASSED - {current_task.description}")

            if feedback:
                self._log_success_details(feedback)

            # Save checkpoint (Phase 3)
            if self.checkpoint_manager:
                self.checkpoint_manager.save_checkpoint(
                    state=state,
                    task_idx=current_idx,
                    tag="completed"
                )

            return {
                "tasks": tasks,
                "current_task_idx": current_idx + 1,
                "retry_count": 0,
                "status": f"task_{current_idx}_passed"
            }
        else:
            # Failure - log details
            print(f"[CRITIC] Task {current_idx} FAILED - {current_task.description}")

            if feedback:
                self._log_failure_details(feedback)
            elif exec_result:
                print(f"[CRITIC] Error: {exec_result.error}")

            if retry_count < max_retries:
                # Retry with RetryContext (Phase 3)
                print(f"[CRITIC] Retrying task {current_idx} (attempt {retry_count + 1}/{max_retries})")

                # Rollback failed code
                file_map = state.get("file_map", {})
                target_file = current_task.target_file
                generated_code = state.get("generated_code", "")

                if target_file in file_map:
                    if generated_code and file_map[target_file].content.endswith(generated_code):
                        file_map[target_file].content = file_map[target_file].content[:-len(generated_code)].rstrip()
                        print(f"[CRITIC] Rolled back failed code from {target_file}")

                # Create RetryContext for differentiated error handling
                retry_context = self._create_retry_context(
                    feedback=feedback,
                    failed_code=generated_code,
                    attempt=retry_count + 1,
                    max_attempts=max_retries,
                    previous_context=state.get("retry_context")
                )

                return {
                    "tasks": tasks,
                    "file_map": file_map,
                    "current_task_idx": current_idx,
                    "retry_count": retry_count + 1,
                    "retry_context": retry_context,
                    "status": f"task_{current_idx}_retry_{retry_count + 1}"
                }
            else:
                # Max retries reached
                print(f"[CRITIC] Max retries reached for task {current_idx}, skipping")
                return {
                    "tasks": tasks,
                    "current_task_idx": current_idx + 1,
                    "retry_count": 0,
                    "status": f"task_{current_idx}_failed_max_retries"
                }

    def _log_success_details(self, feedback: FeedbackResult):
        """성공 시 상세 정보 로깅"""
        print(f"[CRITIC] Summary: {feedback.summary}")

        # Lint warnings (non-blocking)
        warnings = [e for e in feedback.lint_errors if e.severity == "warning"]
        if warnings:
            print(f"[CRITIC] Note: {len(warnings)} lint warning(s)")
            for w in warnings[:3]:
                print(f"  - Line {w.line}: {w.code} {w.message}")

    def _log_failure_details(self, feedback: FeedbackResult):
        """실패 시 에러 타입별 상세 로깅"""
        print(f"[CRITIC] Summary: {feedback.summary}")

        # 1. Syntax errors
        if not feedback.syntax_valid:
            print("[CRITIC] ERROR TYPE: Syntax Error")
            for err in feedback.syntax_errors[:3]:
                print(f"  - {err}")
            return

        # 2. Lint errors
        if not feedback.lint_passed:
            print("[CRITIC] ERROR TYPE: Lint Error")
            critical = [e for e in feedback.lint_errors if e.severity == "error"]
            for err in critical[:3]:
                print(f"  - Line {err.line}: [{err.code}] {err.message}")
            return

        # 3. Test failures
        if not feedback.tests_passed:
            print("[CRITIC] ERROR TYPE: Test Failure")
            failed_tests = [t for t in feedback.test_results if not t.passed]
            for t in failed_tests[:3]:
                print(f"  - {t.name}: {t.error_message}")
                if t.traceback:
                    # Show last 3 lines of traceback
                    tb_lines = t.traceback.strip().split('\n')
                    for line in tb_lines[-3:]:
                        print(f"    {line}")

    def _create_retry_context(
        self,
        feedback: FeedbackResult,
        failed_code: str,
        attempt: int,
        max_attempts: int,
        previous_context: RetryContext = None
    ) -> RetryContext:
        """
        Create RetryContext with error-specific information (Phase 3)

        Determines error type and generates detailed context for code_writer
        to generate better fixes.
        """
        # Determine error type
        if not feedback.syntax_valid:
            error_type = "syntax"
            error_details = "\n".join(feedback.syntax_errors)
        elif not feedback.lint_passed:
            error_type = "lint"
            critical_errors = [e for e in feedback.lint_errors if e.severity == "error"]
            error_details = "\n".join([
                f"Line {e.line}: [{e.code}] {e.message}"
                for e in critical_errors[:5]
            ])
        elif not feedback.tests_passed:
            error_type = "test"
            failed_tests = [t for t in feedback.test_results if not t.passed]
            error_details = "\n".join([
                f"{t.name}: {t.error_message}"
                for t in failed_tests[:3]
            ])
        else:
            # Unknown error
            error_type = "runtime"
            error_details = feedback.summary

        # Track error history
        previous_errors = []
        if previous_context and previous_context.error_details:
            previous_errors = previous_context.previous_errors + [previous_context.error_details]
            # Keep last 3 errors only
            previous_errors = previous_errors[-3:]

        print(f"[CRITIC] Creating RetryContext: type={error_type}, attempt={attempt}/{max_attempts}")

        return RetryContext(
            error_type=error_type,
            failed_code=failed_code,
            error_details=error_details,
            attempt=attempt,
            max_attempts=max_attempts,
            previous_errors=previous_errors
        )


# Backward compatibility alias
CriticV2 = Critic
