"""
TestGenerator Node - 파일별 종합 테스트 생성

Reasoning model support: <think> tag handling
Logs reasoning traces and execution.
"""
import re
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import AgentState
from graph.llm_utils import (
    extract_response_content,
    extract_think_content,
    log_llm_interaction,
    log_execution
)


SYSTEM_PROMPT = """Generate a comprehensive unit test for the given function.

Requirements:
1. Test multiple cases (happy path, edge cases, errors)
2. Use simple assertions (no pytest imports needed in execution)
3. Test function should be standalone
4. Return ONLY the test function code

Example:
def test_add():
    # Happy path
    assert add(2, 3) == 5
    assert add(0, 0) == 0

    # Negatives
    assert add(-1, 1) == 0
    assert add(-5, -3) == -8

    # Floats
    assert add(2.5, 1.5) == 4.0
"""


class TestGenerator:
    """Generates comprehensive tests for accumulated file"""

    def __init__(self, llm: ChatOpenAI, workspace_dir: str = None):
        self.llm = llm
        self.workspace_dir = workspace_dir

    async def generate_test_for_file(self, file_path: str, file_content: str) -> str:
        """Generate comprehensive test for entire file"""
        prompt = f"""Generate comprehensive unit tests for this file:

File: {file_path}
Content:
{file_content}

Generate ONE test function for EACH function in the file.
All test functions should be in one response."""

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)

        # Extract content and remove <think> tags from reasoning models
        raw_content = response.content if hasattr(response, 'content') else str(response)
        reasoning_trace = extract_think_content(raw_content)
        content = extract_response_content(response)

        # Log interaction
        if self.workspace_dir:
            log_llm_interaction(
                workspace_dir=self.workspace_dir,
                node_name="test_generator",
                prompt=prompt[:1000],
                response=content[:1000],
                reasoning_trace=reasoning_trace,
                metadata={"file": file_path, "content_length": len(file_content)}
            )

        # Extract all test functions
        test_functions = re.findall(r'def test_\w+.*?(?=\ndef\s|\Z)', content, re.DOTALL)

        if test_functions:
            return '\n\n'.join(test_functions)
        else:
            # Fallback
            return f"# Tests for {file_path}\ndef test_placeholder():\n    pass"

    async def arun(self, state: AgentState) -> Dict[str, Any]:
        """Generate tests for all files"""
        file_map = state.get("file_map", {})

        print(f"[TEST_GENERATOR] Generating tests for {len(file_map)} files")

        # Collect files to process (avoid modifying dict during iteration)
        files_to_test = [
            (file_path, file_state)
            for file_path, file_state in file_map.items()
            if not file_path.startswith("test_") and file_state.content
        ]

        for file_path, file_state in files_to_test:
            # Generate tests
            test_code = await self.generate_test_for_file(file_path, file_state.content)

            # Create or update test file
            test_file_path = f"test_{file_path}"
            if test_file_path not in file_map:
                from graph.state import FileState
                file_map[test_file_path] = FileState(
                    path=test_file_path,
                    purpose=f"Tests for {file_path}"
                )

            file_map[test_file_path].content = test_code
            file_map[test_file_path].has_tests = True

            print(f"[TEST_GENERATOR] Generated {len(test_code)} chars of tests for {file_path}")

        result = {
            "file_map": file_map,
            "status": "tests_generated"
        }

        # Log execution
        if self.workspace_dir:
            log_execution(self.workspace_dir, "test_generator", result)

        return result

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Sync wrapper"""
        import asyncio
        return asyncio.run(self.arun(state))
