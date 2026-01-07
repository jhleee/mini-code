import os
from typing import Dict, Any, List
from graph.state import AgentState


class RetrieverV2:
    """Retrieves context from workspace files for current task"""

    def __init__(self, workspace_dir: str = "workspace"):
        self.workspace_dir = workspace_dir

    def search_files(self, keywords: List[str]) -> str:
        """Simple file-based context search"""
        context_parts = []

        if not os.path.exists(self.workspace_dir):
            return "No existing workspace files found."

        for root, dirs, files in os.walk(self.workspace_dir):
            for file in files:
                if file.endswith(('.py', '.js', '.java', '.md')):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Simple keyword matching
                            if any(kw.lower() in content.lower() for kw in keywords):
                                context_parts.append(f"File: {filepath}\n{content[:500]}\n")
                    except Exception:
                        continue

        if not context_parts:
            return "No relevant files found in workspace."

        return "\n---\n".join(context_parts[:5])

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Retrieve context for current task"""
        current_idx = state.get("current_task_idx", 0)
        tasks = state.get("tasks", [])

        if current_idx >= len(tasks):
            return {"context": "No more tasks to process."}

        current_task = tasks[current_idx]

        # Use task description as keywords
        keywords = current_task.description.split()[:5]

        context = self.search_files(keywords)

        return {
            "context": context,
            "status": f"retrieval_complete_task_{current_idx}"
        }


# Backward compatibility alias
Retriever = RetrieverV2
