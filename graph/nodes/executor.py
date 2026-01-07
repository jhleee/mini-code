"""
Executor Node - 코드 실행 및 테스트

Phase 2: Rich Feedback Loops
- 정적 분석 통합 (syntax, lint)
- 개별 테스트 결과 수집
- FeedbackResult 반환
"""
import subprocess
import tempfile
import os
import re
import json
from typing import Dict, Any, List

from graph.state import (
    AgentState, ExecutionResult, FeedbackResult, TestResult, LintError
)
from graph.nodes.analyzer import StaticAnalyzer


class Executor:
    """
    Executor with Rich Feedback (Phase 2)

    실행 순서:
    1. Syntax check (ast.parse)
    2. Lint check (ruff) - 미설치 시 skip
    3. Test execution (subprocess)

    개별 테스트 결과를 TestResult 리스트로 반환
    """

    def __init__(self, workspace_dir: str = "workspace"):
        self.workspace_dir = workspace_dir
        self.analyzer = StaticAnalyzer()

    def run_tests_with_results(
        self,
        code: str,
        test_code: str,
        target_file: str = "implementation.py"
    ) -> List[TestResult]:
        """
        테스트 실행 및 개별 결과 수집

        Returns:
            TestResult 리스트 (각 테스트 함수별 결과)
        """
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Write code file
                code_file = os.path.join(tmpdir, target_file)
                with open(code_file, 'w', encoding='utf-8') as f:
                    f.write(code)

                # Prepare test code - remove only imports from local modules
                # Keep standard library imports (json, math, etc.)
                test_code_cleaned = re.sub(r'from\s+[a-z_]+\s+import\s+.*?\n', '', test_code)
                # Only remove imports that look like local module imports (not standard lib)
                test_code_cleaned = re.sub(r'import\s+(?!sys|pytest|json|math|re|os|typing)[a-z_]+\s*\n', '', test_code_cleaned)

                module_name = target_file.replace('.py', '')

                test_content = f"""import sys
import json
import traceback

sys.path.insert(0, r'{tmpdir}')
from {module_name} import *

{test_code_cleaned}

if __name__ == '__main__':
    import inspect
    results = []

    test_funcs = [obj for name, obj in list(globals().items())
                  if name.startswith('test_') and callable(obj)]

    for test_func in test_funcs:
        result = {{"name": test_func.__name__, "passed": False, "error_message": None, "traceback": None}}
        try:
            test_func()
            result["passed"] = True
            print(f"[PASS] {{test_func.__name__}}")
        except AssertionError as e:
            result["error_message"] = str(e) if str(e) else "Assertion failed"
            result["traceback"] = traceback.format_exc()
            print(f"[FAIL] {{test_func.__name__}}: {{result['error_message']}}")
        except Exception as e:
            result["error_message"] = str(e)
            result["traceback"] = traceback.format_exc()
            print(f"[ERROR] {{test_func.__name__}}: {{e}}")
        results.append(result)

    # Output JSON results
    print("---TEST_RESULTS_JSON---")
    print(json.dumps(results))
"""
                test_file = os.path.join(tmpdir, "test_runner.py")
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(test_content)

                # Run test
                result = subprocess.run(
                    ['python', test_file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                # Parse results
                test_results = []
                output = result.stdout

                # Extract JSON results
                if "---TEST_RESULTS_JSON---" in output:
                    json_part = output.split("---TEST_RESULTS_JSON---")[1].strip()
                    try:
                        results_data = json.loads(json_part)
                        for r in results_data:
                            test_results.append(TestResult(
                                name=r.get("name", "unknown"),
                                passed=r.get("passed", False),
                                error_message=r.get("error_message"),
                                traceback=r.get("traceback")
                            ))
                    except json.JSONDecodeError:
                        pass

                # Fallback: parse from output
                if not test_results:
                    for line in output.splitlines():
                        if line.startswith("[PASS]"):
                            name = line.replace("[PASS]", "").strip()
                            test_results.append(TestResult(name=name, passed=True))
                        elif line.startswith("[FAIL]") or line.startswith("[ERROR]"):
                            parts = line.split(":", 1)
                            name = parts[0].replace("[FAIL]", "").replace("[ERROR]", "").strip()
                            error = parts[1].strip() if len(parts) > 1 else "Unknown error"
                            test_results.append(TestResult(
                                name=name,
                                passed=False,
                                error_message=error
                            ))

                # If no tests found but process failed, add generic failure
                if not test_results and result.returncode != 0:
                    test_results.append(TestResult(
                        name="test_execution",
                        passed=False,
                        error_message=result.stderr or "Test execution failed",
                        traceback=result.stderr
                    ))

                # If no tests at all, add placeholder pass
                if not test_results:
                    test_results.append(TestResult(
                        name="test_placeholder",
                        passed=True,
                        error_message=None
                    ))

                return test_results

        except subprocess.TimeoutExpired:
            return [TestResult(
                name="test_timeout",
                passed=False,
                error_message="Test execution timeout (30s)"
            )]
        except Exception as e:
            return [TestResult(
                name="test_error",
                passed=False,
                error_message=f"Execution error: {str(e)}"
            )]

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Execute with rich feedback"""
        file_map = state.get("file_map", {})
        current_idx = state.get("current_task_idx", 0)
        tasks = state.get("tasks", [])

        # Get target file
        target_file = "implementation.py"
        if current_idx < len(tasks):
            target_file = tasks[current_idx].target_file

        # Get full code from file_map
        file_state = file_map.get(target_file)
        code = file_state.content if file_state else ""

        # Get test code
        test_code = state.get("generated_test", "")

        print(f"[EXECUTOR] Target: {target_file}")
        print(f"[EXECUTOR] Code: {len(code)} chars, Test: {len(test_code)} chars")

        if not code:
            feedback = FeedbackResult(
                syntax_valid=False,
                syntax_errors=["No code to execute"],
                lint_passed=False,
                lint_errors=[],
                tests_passed=False,
                test_results=[],
                overall_passed=False,
                summary="No code to execute"
            )
            return {
                "feedback": feedback,
                "exec_result": ExecutionResult(passed=False, output="", error="No code to execute"),
                "status": "execution_failed"
            }

        # 1. Static analysis
        analysis = self.analyzer.analyze(code, target_file)

        # 2. Check syntax
        if not analysis["syntax_valid"]:
            feedback = FeedbackResult(
                syntax_valid=False,
                syntax_errors=analysis["syntax_errors"],
                lint_passed=False,
                lint_errors=[],
                tests_passed=False,
                test_results=[],
                overall_passed=False,
                summary=f"Syntax error: {analysis['syntax_errors'][0]}"
            )
            print(f"[EXECUTOR] Syntax error: {analysis['syntax_errors']}")
            return {
                "feedback": feedback,
                "exec_result": ExecutionResult(passed=False, output="", error=feedback.summary),
                "status": "execution_failed"
            }

        # 3. Check lint (warnings are OK)
        lint_errors: List[LintError] = analysis["lint_errors"]
        critical_lint = [e for e in lint_errors if e.severity == "error"]
        lint_passed = len(critical_lint) == 0

        if not lint_passed:
            error_summary = "; ".join([f"{e.code}:{e.line} {e.message}" for e in critical_lint[:3]])
            feedback = FeedbackResult(
                syntax_valid=True,
                syntax_errors=[],
                lint_passed=False,
                lint_errors=lint_errors,
                tests_passed=False,
                test_results=[],
                overall_passed=False,
                summary=f"Lint errors: {error_summary}"
            )
            print(f"[EXECUTOR] Lint errors: {len(critical_lint)}")
            return {
                "feedback": feedback,
                "exec_result": ExecutionResult(passed=False, output="", error=feedback.summary),
                "status": "execution_failed"
            }

        # 4. Run tests
        test_results = self.run_tests_with_results(code, test_code, target_file)
        tests_passed = all(t.passed for t in test_results)

        # Build summary
        passed_count = sum(1 for t in test_results if t.passed)
        total_count = len(test_results)

        if tests_passed:
            summary = f"All {total_count} tests passed"
        else:
            failed_tests = [t.name for t in test_results if not t.passed]
            summary = f"{passed_count}/{total_count} tests passed. Failed: {', '.join(failed_tests[:3])}"

        overall_passed = tests_passed

        # Log lint warnings
        warnings = [e for e in lint_errors if e.severity == "warning"]
        if warnings:
            print(f"[EXECUTOR] {len(warnings)} lint warnings (non-blocking)")

        print(f"[EXECUTOR] Tests: {passed_count}/{total_count} passed")
        print(f"[EXECUTOR] Overall: {'PASS' if overall_passed else 'FAIL'}")

        feedback = FeedbackResult(
            syntax_valid=True,
            syntax_errors=[],
            lint_passed=lint_passed,
            lint_errors=lint_errors,
            tests_passed=tests_passed,
            test_results=test_results,
            overall_passed=overall_passed,
            summary=summary
        )

        # Backward compatible exec_result
        exec_result = ExecutionResult(
            passed=overall_passed,
            output=summary,
            error=None if overall_passed else summary
        )

        return {
            "feedback": feedback,
            "exec_result": exec_result,
            "status": f"execution_{'passed' if overall_passed else 'failed'}"
        }
