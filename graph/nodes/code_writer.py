"""
CodeWriter Node - 태스크별 코드 생성

Phase 1: Structured Output 적용
- with_structured_output()으로 CodeWriterOutput 스키마 강제
- generated_code와 generated_test 분리 반환
- Reasoning model support: <think> tag handling
"""
import json
import re
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import AgentState, CodeWriterOutput
from graph.llm_utils import extract_response_content


SYSTEM_PROMPT = """You are an expert software engineer writing clean, production-ready code.

CRITICAL: You are adding code to an EXISTING FILE. Generate ONLY the new function/class to append.

Requirements:
1. Write complete, runnable code (not pseudocode)
2. Include type hints for all parameters and return values
3. Add clear docstrings explaining the function
4. Follow Python best practices (PEP8)
5. Return ONLY the code snippet to append (no imports unless new dependency)

For test_code:
- Write at least 2 test cases (happy path + edge case)
- Use assert statements
- Test function name should start with 'test_'
"""


class CodeWriter:
    """
    CodeWriter with Structured Output (Phase 1)

    Uses llm.with_structured_output() to enforce CodeWriterOutput schema.
    Returns generated_code and generated_test separately.
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        # Structured output을 지원하는 LLM으로 변환
        self.structured_llm = llm.with_structured_output(CodeWriterOutput)

    async def arun(self, state: AgentState) -> Dict[str, Any]:
        """Generate code snippet using structured output"""
        current_idx = state.get("current_task_idx", 0)
        tasks = state.get("tasks", [])

        if current_idx >= len(tasks):
            return {"status": "no_more_tasks"}

        current_task = tasks[current_idx]
        target_file = current_task.target_file
        context = state.get("context", "")

        # Get current file content
        file_map = state.get("file_map", {})
        file_state = file_map.get(target_file)
        current_content = file_state.content if file_state else ""

        prompt = f"""Task: {current_task.description}

Target file: {target_file}
Action: {current_task.action}

Current file content:
```python
{current_content if current_content else "# Empty file"}
```

Context from workspace:
{context}

Generate the code snippet to {current_task.action}."""

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]

        print(f"[CODE_WRITER] Task {current_idx}: {current_task.description}")
        print(f"[CODE_WRITER] Target: {target_file} ({current_task.action})")

        try:
            # Structured output으로 직접 CodeWriterOutput 객체 반환
            result: CodeWriterOutput = await self.structured_llm.ainvoke(messages)

            code = result.code
            test_code = result.test_code
            imports = result.imports

            print(f"[CODE_WRITER] Structured output: code={len(code)} chars, test={len(test_code)} chars")

            # Validate syntax - structured output may have escape issues
            if code and not self._validate_syntax(code):
                print(f"[CODE_WRITER] Structured output has syntax error, falling back...")
                code, test_code = await self._fallback_parse(messages)
                imports = []
            elif imports:
                print(f"[CODE_WRITER] New imports: {imports}")

        except Exception as e:
            print(f"[CODE_WRITER] Structured output failed: {e}")
            print("[CODE_WRITER] Falling back to regex parsing...")

            # Fallback: 기존 방식
            code, test_code = await self._fallback_parse(messages)
            imports = []

        return {
            "generated_code": code,
            "generated_test": test_code,
            "status": f"code_generated_task_{current_idx}"
        }

    async def _fallback_parse(self, messages: list) -> tuple:
        """Fallback: regex 기반 파싱 (structured output 실패 시)"""
        response = await self.llm.ainvoke(messages)

        # Extract content and remove <think> tags from reasoning models
        content = extract_response_content(response)

        # Try JSON extraction
        result = self._extract_json_from_markdown(content)
        if result and "code" in result:
            return result.get("code", ""), result.get("test_code", "")

        # Try code block extraction
        print("[CODE_WRITER] JSON failed, extracting code blocks...")
        all_blocks = re.findall(r'```(?:python)?\n(.*?)```', content, re.DOTALL)

        code = all_blocks[0].strip() if len(all_blocks) > 0 else ""
        test_code = all_blocks[1].strip() if len(all_blocks) > 1 else "def test_placeholder():\n    pass"

        return code, test_code

    def _validate_syntax(self, code: str) -> bool:
        """Check if code has valid Python syntax"""
        import ast
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _extract_json_from_markdown(self, text: str) -> dict:
        """Extract JSON from markdown (fallback용)"""
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        try:
            return json.loads(text)
        except:
            return None

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Sync wrapper for LangGraph compatibility"""
        import asyncio
        return asyncio.run(self.arun(state))


# Backward compatibility alias
CodeWriterV2 = CodeWriter
