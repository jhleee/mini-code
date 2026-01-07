import os
from typing import Dict, Any
from graph.state import AgentState


class RepoManagerV2:
    """Saves accumulated files to workspace"""

    def __init__(self, workspace_dir: str = "workspace"):
        self.workspace_dir = workspace_dir
        os.makedirs(workspace_dir, exist_ok=True)

    def save_file(self, filename: str, content: str) -> str:
        """Save file to workspace"""
        filepath = os.path.join(self.workspace_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Save all files from file_map"""
        file_map = state.get("file_map", {})
        tasks = state.get("tasks", [])
        final_files = {}

        print(f"[REPO_MANAGER_V2] Saving {len(file_map)} files")

        # Save all files
        for file_path, file_state in file_map.items():
            if not file_state.content:
                print(f"[REPO_MANAGER_V2] Skipping empty file: {file_path}")
                continue

            filepath = self.save_file(file_path, file_state.content)
            final_files[file_path] = filepath

            print(f"[REPO_MANAGER_V2] Saved {file_path}: {len(file_state.content)} chars, {len(file_state.functions)} functions")

        # Generate summary report
        completed = sum(1 for t in tasks if t.completed)
        total = len(tasks)

        summary = f"""# Implementation Summary

## File Structure
"""
        for file_path, file_state in file_map.items():
            if file_state.content:
                func_list = ', '.join(file_state.functions) if file_state.functions else "N/A"
                summary += f"- **{file_path}**: {file_state.purpose}\n"
                summary += f"  - Functions: {func_list}\n"
                summary += f"  - Size: {len(file_state.content)} characters\n"

        summary += f"""
## Task Completion
Total tasks: {total}
Completed: {completed}
Failed: {total - completed}

## Task Details
"""
        for task in tasks:
            status = "✓" if task.completed else "✗"
            summary += f"{status} Task {task.task_id} ({task.target_file}): {task.description}\n"

        summary_path = self.save_file("SUMMARY.md", summary)
        final_files["SUMMARY.md"] = summary_path

        return {
            "final_files": final_files,
            "status": "complete"
        }


# Backward compatibility alias
RepoManager = RepoManagerV2
