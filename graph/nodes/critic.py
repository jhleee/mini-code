"""
Critic Node - 실행 결과 평가 및 재시도 결정

Phase 2: Rich Feedback Loops
- feedback 필드 사용 (FeedbackResult)
- 에러 타입별 상세 로깅
- 호환성을 위해 exec_result도 지원
"""
from typing import Dict, Any
from graph.state import AgentState, FeedbackResult


class Critic:
    """
    Critic with Rich Feedback (Phase 2)

    FeedbackResult를 사용하여 에러 타입별 상세 정보 로깅
    """

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
                # Retry
                print(f"[CRITIC] Retrying task {current_idx} (attempt {retry_count + 1}/{max_retries})")

                # Rollback failed code
                file_map = state.get("file_map", {})
                target_file = current_task.target_file
                if target_file in file_map:
                    generated_code = state.get("generated_code", "")
                    if generated_code and file_map[target_file].content.endswith(generated_code):
                        file_map[target_file].content = file_map[target_file].content[:-len(generated_code)].rstrip()
                        print(f"[CRITIC] Rolled back failed code from {target_file}")

                return {
                    "tasks": tasks,
                    "file_map": file_map,
                    "current_task_idx": current_idx,
                    "retry_count": retry_count + 1,
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


# Backward compatibility alias
CriticV2 = Critic
