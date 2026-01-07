"""
Planner Node - PRD를 분석하여 파일 구조와 태스크를 생성

Phase 1: Structured Output 적용
- with_structured_output()으로 Pydantic 모델 강제
- regex 파싱 제거, 파싱 에러 방지
"""
import json
import re
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import AgentState, FileState, Task, PlannerOutput


SYSTEM_PROMPT = """You are a senior software engineer planning file structure and implementation tasks.

Your job: Analyze the PRD and create a FILE-CENTRIC plan.

CRITICAL RULES:
1. Group related functions into SINGLE FILES (e.g., all calculator functions in calculator.py)
2. Plan file structure BEFORE breaking down tasks
3. Each task targets ONE file and adds/modifies ONE function
4. Do NOT include test files in the file list - tests are auto-generated later

Example for calculator PRD:
- ONE file: calculator.py with purpose "Core arithmetic operations"
- FOUR tasks: add, subtract, multiply, divide (all target calculator.py)
"""


class Planner:
    """
    Planner with Structured Output (Phase 1)

    Uses llm.with_structured_output() to enforce PlannerOutput schema.
    Falls back to regex parsing if structured output fails.
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        # Structured output을 지원하는 LLM으로 변환
        self.structured_llm = llm.with_structured_output(PlannerOutput)

    async def arun(self, state: AgentState) -> Dict[str, Any]:
        """Create file-centric plan from PRD using structured output"""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"PRD:\n{state['prd_content']}")
        ]

        try:
            # Structured output으로 직접 PlannerOutput 객체 반환
            result: PlannerOutput = await self.structured_llm.ainvoke(messages)

            print(f"[PLANNER] Structured output received: {len(result.files)} files, {len(result.tasks)} tasks")

            # Build file map from FileSpec
            file_map = {}
            for file_spec in result.files:
                file_state = FileState(
                    path=file_spec.path,
                    purpose=file_spec.purpose,
                    functions=file_spec.functions
                )
                file_map[file_spec.path] = file_state

            # Build task list from TaskSpec
            tasks = [
                Task(
                    task_id=task_spec.task_id,
                    target_file=task_spec.target_file,
                    action=task_spec.action,
                    description=task_spec.description
                )
                for task_spec in result.tasks
            ]

            print(f"[PLANNER] Planned {len(file_map)} files, {len(tasks)} tasks")
            for f in file_map.values():
                print(f"  - {f.path}: {f.purpose}")

        except Exception as e:
            print(f"[PLANNER] Structured output failed: {e}")
            print("[PLANNER] Falling back to regex parsing...")

            # Fallback: 기존 regex 방식으로 재시도
            file_map, tasks = await self._fallback_parse(state)

        return {
            "file_map": file_map,
            "tasks": tasks,
            "current_task_idx": 0,
            "retry_count": 0,
            "max_retries": 3,
            "status": "planning_complete"
        }

    async def _fallback_parse(self, state: AgentState) -> tuple:
        """Fallback: regex 기반 JSON 파싱 (structured output 실패 시)"""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT + "\n\nReturn ONLY valid JSON."),
            HumanMessage(content=f"PRD:\n{state['prd_content']}")
        ]

        response = await self.llm.ainvoke(messages)

        try:
            json_str = self._extract_json(response.content)
            result = json.loads(json_str)

            file_map = {}
            for file_data in result.get("files", []):
                file_state = FileState(
                    path=file_data["path"],
                    purpose=file_data["purpose"],
                    functions=file_data.get("functions", [])
                )
                file_map[file_data["path"]] = file_state

            tasks = [
                Task(
                    task_id=t["task_id"],
                    target_file=t["target_file"],
                    action=t.get("action", "append"),
                    description=t["description"]
                )
                for t in result.get("tasks", [])
            ]

            print(f"[PLANNER] Fallback parsing successful: {len(file_map)} files, {len(tasks)} tasks")
            return file_map, tasks

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[PLANNER] Fallback parsing also failed: {e}")
            # 최후의 수단: 기본 계획
            file_map = {
                "implementation.py": FileState(
                    path="implementation.py",
                    purpose="Implementation from PRD"
                )
            }
            tasks = [
                Task(
                    task_id=1,
                    target_file="implementation.py",
                    action="create",
                    description=state['prd_content'][:100]
                )
            ]
            return file_map, tasks

    def _extract_json(self, text: str) -> str:
        """Extract JSON from text (fallback용)"""
        # Try markdown code block
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            return match.group(1)

        # Try direct JSON
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)

        return text

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Sync wrapper for LangGraph compatibility"""
        import asyncio
        return asyncio.run(self.arun(state))


# Backward compatibility alias
PlannerV2 = Planner
