from typing import Dict, Any
from graph.state import AgentState


class FileBuilder:
    """Accumulates code snippets into files"""

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Append generated code to target file"""
        current_idx = state.get("current_task_idx", 0)
        tasks = state.get("tasks", [])

        if current_idx >= len(tasks):
            return {"status": "no_task"}

        current_task = tasks[current_idx]
        generated_code = state.get("generated_code", "")
        file_map = state.get("file_map", {})

        if not generated_code:
            print("[FILE_BUILDER] No code to append")
            return {"status": "no_code"}

        # Get target file (auto-create if not exists)
        target_file = current_task.target_file
        if target_file not in file_map:
            print(f"[FILE_BUILDER] Auto-creating file: {target_file}")
            from graph.state import FileState
            file_map[target_file] = FileState(
                path=target_file,
                purpose=current_task.description[:50]
            )

        file_state = file_map[target_file]

        # Append code with proper spacing
        if file_state.content:
            file_state.content += "\n\n" + generated_code
        else:
            file_state.content = generated_code

        # Update function list
        # Extract function name from code
        import re
        func_match = re.search(r'def\s+(\w+)\s*\(', generated_code)
        if func_match:
            func_name = func_match.group(1)
            if func_name not in file_state.functions:
                file_state.functions.append(func_name)
                print(f"[FILE_BUILDER] Added {func_name}() to {target_file}")

        print(f"[FILE_BUILDER] {target_file} now has {len(file_state.content)} chars, {len(file_state.functions)} functions")

        return {
            "file_map": file_map,
            "status": "file_updated"
        }
