"""
Static Analyzer - 코드 정적 분석

Phase 2: Rich Feedback Loops
- syntax check (ast.parse)
- lint check (ruff) - 미설치 시 graceful skip
- type check (mypy) - 미설치 시 graceful skip
"""
import ast
import subprocess
import json
import shutil
import tempfile
import os
from pathlib import Path
from typing import Tuple, List, Optional

from graph.state import LintError


class StaticAnalyzer:
    """
    정적 분석기 - syntax, lint, type 검사

    ruff/mypy가 미설치된 경우 graceful skip
    """

    def __init__(self):
        # 도구 설치 여부 확인
        self._ruff_available = shutil.which("ruff") is not None
        self._mypy_available = shutil.which("mypy") is not None

        if not self._ruff_available:
            print("[ANALYZER] Warning: ruff not installed. Run 'pip install ruff' for lint checks.")
        if not self._mypy_available:
            print("[ANALYZER] Warning: mypy not installed. Run 'pip install mypy' for type checks.")

    def check_syntax(self, code: str) -> Tuple[bool, List[str]]:
        """
        Python syntax 검사 (ast.parse 사용)

        Returns:
            (valid, errors): 문법 유효 여부, 에러 메시지 리스트
        """
        try:
            ast.parse(code)
            return True, []
        except SyntaxError as e:
            error_msg = f"Line {e.lineno}: {e.msg}"
            if e.text:
                error_msg += f"\n  {e.text.strip()}"
                if e.offset:
                    error_msg += f"\n  {' ' * (e.offset - 1)}^"
            return False, [error_msg]
        except Exception as e:
            return False, [f"Parse error: {str(e)}"]

    def run_ruff(self, code: str, filename: str = "code.py") -> List[LintError]:
        """
        ruff 린트 검사

        Args:
            code: 검사할 코드
            filename: 가상 파일명 (에러 메시지용)

        Returns:
            LintError 리스트
        """
        if not self._ruff_available:
            return []

        # 임시 파일에 코드 저장
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                ["ruff", "check", temp_path, "--output-format", "json", "--select", "E,W,F"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return []

            errors = []
            try:
                lint_results = json.loads(result.stdout)
                for item in lint_results:
                    severity = "error" if item.get("code", "").startswith(("E", "F")) else "warning"
                    errors.append(LintError(
                        file=filename,
                        line=item.get("location", {}).get("row", 0),
                        column=item.get("location", {}).get("column", 0),
                        code=item.get("code", ""),
                        message=item.get("message", ""),
                        severity=severity
                    ))
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 텍스트 출력 파싱
                if result.stdout:
                    errors.append(LintError(
                        file=filename,
                        line=0,
                        column=0,
                        code="PARSE_ERROR",
                        message=result.stdout[:200],
                        severity="error"
                    ))

            return errors

        except subprocess.TimeoutExpired:
            return [LintError(
                file=filename,
                line=0,
                column=0,
                code="TIMEOUT",
                message="Ruff analysis timed out (30s)",
                severity="error"
            )]
        except Exception as e:
            return [LintError(
                file=filename,
                line=0,
                column=0,
                code="RUFF_ERROR",
                message=str(e),
                severity="error"
            )]
        finally:
            # 임시 파일 삭제
            try:
                os.unlink(temp_path)
            except:
                pass

    def run_mypy(self, code: str, filename: str = "code.py") -> List[str]:
        """
        mypy 타입 검사

        Args:
            code: 검사할 코드
            filename: 가상 파일명

        Returns:
            에러 메시지 리스트
        """
        if not self._mypy_available:
            return []

        # 임시 파일에 코드 저장
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                ["mypy", temp_path, "--no-error-summary", "--no-color"],
                capture_output=True,
                text=True,
                timeout=60
            )

            errors = []
            for line in result.stdout.splitlines():
                if ": error:" in line:
                    # mypy 에러 포맷: file.py:line: error: message
                    errors.append(line.replace(temp_path, filename))

            return errors

        except subprocess.TimeoutExpired:
            return ["mypy analysis timed out (60s)"]
        except Exception as e:
            return [f"mypy error: {str(e)}"]
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass

    def analyze(self, code: str, filename: str = "code.py") -> dict:
        """
        종합 정적 분석

        Returns:
            {
                "syntax_valid": bool,
                "syntax_errors": List[str],
                "lint_passed": bool,
                "lint_errors": List[LintError],
                "type_errors": List[str]
            }
        """
        # 1. Syntax check (필수)
        syntax_valid, syntax_errors = self.check_syntax(code)

        # syntax 실패 시 다른 분석 스킵
        if not syntax_valid:
            return {
                "syntax_valid": False,
                "syntax_errors": syntax_errors,
                "lint_passed": False,
                "lint_errors": [],
                "type_errors": []
            }

        # 2. Lint check
        lint_errors = self.run_ruff(code, filename)
        # critical 에러만 실패로 처리
        critical_lint = [e for e in lint_errors if e.severity == "error"]
        lint_passed = len(critical_lint) == 0

        # 3. Type check (optional)
        type_errors = self.run_mypy(code, filename)

        return {
            "syntax_valid": True,
            "syntax_errors": [],
            "lint_passed": lint_passed,
            "lint_errors": lint_errors,
            "type_errors": type_errors
        }

    @property
    def tools_status(self) -> dict:
        """설치된 도구 상태 반환"""
        return {
            "ruff": self._ruff_available,
            "mypy": self._mypy_available
        }
