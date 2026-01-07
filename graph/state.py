from typing import TypedDict, List, Dict, Optional, Literal
from pydantic import BaseModel


# ============================================================
# Phase 1: Structured Output Models
# ============================================================

class FileSpec(BaseModel):
    """File specification from planner (structured output)"""
    path: str
    purpose: str
    functions: List[str] = []


class TaskSpec(BaseModel):
    """Task specification from planner (structured output)"""
    task_id: int
    target_file: str
    action: Literal["create", "append", "modify"]
    description: str


class PlannerOutput(BaseModel):
    """Structured output from planner - replaces regex JSON parsing"""
    files: List[FileSpec]
    tasks: List[TaskSpec]


class CodeWriterOutput(BaseModel):
    """Structured output from code writer - replaces markdown parsing"""
    code: str
    test_code: str
    imports: List[str] = []


# ============================================================
# Phase 2: Rich Feedback Models
# ============================================================

class LintError(BaseModel):
    """Single lint error from ruff"""
    file: str
    line: int
    column: int
    code: str  # E501, W503 등
    message: str
    severity: Literal["error", "warning"]


class TestResult(BaseModel):
    """Individual test result"""
    name: str
    passed: bool
    error_message: Optional[str] = None
    traceback: Optional[str] = None


class FeedbackResult(BaseModel):
    """Rich feedback from execution - replaces simple ExecutionResult"""
    # Syntax check
    syntax_valid: bool
    syntax_errors: List[str] = []

    # Lint check (ruff)
    lint_passed: bool
    lint_errors: List[LintError] = []

    # Test results
    tests_passed: bool
    test_results: List[TestResult] = []

    # Overall
    overall_passed: bool
    summary: str


# ============================================================
# Original Models (kept for compatibility)
# ============================================================


class FileState(BaseModel):
    """State of a single file being built"""
    path: str
    purpose: str
    content: str = ""
    functions: List[str] = []
    has_tests: bool = False


class Task(BaseModel):
    """Single implementation task"""
    task_id: int
    target_file: str
    action: str  # 'create', 'append', 'modify'
    description: str
    search_pattern: Optional[str] = None  # For SEARCH/REPLACE
    completed: bool = False
    code_snippet: Optional[str] = None


class ExecutionResult(BaseModel):
    """Result of code execution"""
    passed: bool
    output: str
    error: Optional[str] = None


class AgentState(TypedDict):
    """File-centric agent state"""
    # Input
    user_query: str
    prd_content: str

    # File Planning
    file_map: Dict[str, FileState]  # path -> FileState
    tasks: List[Task]
    current_task_idx: int

    # Current task execution
    context: str
    generated_code: str
    generated_test: str  # Phase 1: separated test code

    # Feedback (Phase 2: replaces exec_result)
    feedback: FeedbackResult
    exec_result: ExecutionResult  # kept for backward compatibility

    # Control
    retry_count: int
    max_retries: int
    status: str
