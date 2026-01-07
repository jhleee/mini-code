"""
Checkpoint Manager - Filesystem Checkpoint Pattern (Phase 3)

태스크별 상태 저장 및 복구 기능
실패 시 특정 태스크 시점으로 롤백 가능

Pattern: Filesystem Checkpoint (⭐⭐⭐⭐)
- Resume from specific task
- State recovery after failure
- Incremental progress tracking
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class CheckpointManager:
    """
    파일시스템 기반 체크포인트 관리

    Workflow:
    1. 태스크 완료 시 save_checkpoint() 호출
    2. 실패 시 load_checkpoint() 로 복구
    3. 특정 태스크부터 재시작 가능

    Checkpoint structure:
    workspace/
      checkpoints/
        task_0.json
        task_1.json
        ...
        latest.json -> symlink to latest checkpoint
    """

    def __init__(self, workspace_dir: str):
        self.workspace_dir = Path(workspace_dir)
        self.checkpoints_dir = self.workspace_dir / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, state: Dict[str, Any], task_idx: int, tag: str = None):
        """
        Save checkpoint for specific task

        Args:
            state: Current AgentState
            task_idx: Task index to checkpoint
            tag: Optional tag (e.g., "completed", "failed")
        """
        checkpoint_file = self.checkpoints_dir / f"task_{task_idx}.json"

        # Prepare checkpoint data
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "task_idx": task_idx,
            "tag": tag,
            "state": self._serialize_state(state)
        }

        # Write checkpoint
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)

        # Update latest symlink
        latest_file = self.checkpoints_dir / "latest.json"
        try:
            if latest_file.exists() or latest_file.is_symlink():
                latest_file.unlink()
            # Write actual file instead of symlink (Windows compatibility)
            with open(latest_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[CHECKPOINT] Warning: Could not update latest: {e}")

        print(f"[CHECKPOINT] Saved checkpoint for task {task_idx}" + (f" ({tag})" if tag else ""))

    def load_checkpoint(self, task_idx: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint from specific task or latest

        Args:
            task_idx: Task index to load, or None for latest

        Returns:
            Checkpoint data or None if not found
        """
        if task_idx is not None:
            checkpoint_file = self.checkpoints_dir / f"task_{task_idx}.json"
        else:
            checkpoint_file = self.checkpoints_dir / "latest.json"

        if not checkpoint_file.exists():
            print(f"[CHECKPOINT] No checkpoint found at {checkpoint_file}")
            return None

        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)

            print(f"[CHECKPOINT] Loaded checkpoint from task {checkpoint['task_idx']}")
            print(f"[CHECKPOINT] Timestamp: {checkpoint['timestamp']}")

            return checkpoint

        except Exception as e:
            print(f"[CHECKPOINT] Error loading checkpoint: {e}")
            return None

    def restore_state(self, checkpoint: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restore AgentState from checkpoint

        Args:
            checkpoint: Checkpoint data from load_checkpoint()

        Returns:
            Restored AgentState
        """
        state = checkpoint["state"]

        # Deserialize FileState objects
        from graph.state import FileState, Task, FeedbackResult, RetryContext

        if "file_map" in state:
            file_map = {}
            for path, file_data in state["file_map"].items():
                file_map[path] = FileState(**file_data)
            state["file_map"] = file_map

        if "tasks" in state:
            tasks = [Task(**t) for t in state["tasks"]]
            state["tasks"] = tasks

        if state.get("feedback"):
            state["feedback"] = FeedbackResult(**state["feedback"])

        if state.get("retry_context"):
            state["retry_context"] = RetryContext(**state["retry_context"])

        print(f"[CHECKPOINT] Restored state with {len(state.get('tasks', []))} tasks")
        print(f"[CHECKPOINT] Current task index: {state.get('current_task_idx', 0)}")

        return state

    def list_checkpoints(self) -> list:
        """
        List all available checkpoints

        Returns:
            List of checkpoint info dicts
        """
        checkpoints = []

        for checkpoint_file in sorted(self.checkpoints_dir.glob("task_*.json")):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)

                checkpoints.append({
                    "file": checkpoint_file.name,
                    "task_idx": checkpoint["task_idx"],
                    "timestamp": checkpoint["timestamp"],
                    "tag": checkpoint.get("tag")
                })
            except Exception as e:
                print(f"[CHECKPOINT] Error reading {checkpoint_file}: {e}")

        return checkpoints

    def _serialize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize AgentState for JSON storage

        Converts Pydantic models to dicts
        """
        serialized = {}

        for key, value in state.items():
            if value is None:
                serialized[key] = None
            elif hasattr(value, "dict"):
                # Pydantic model
                serialized[key] = value.dict()
            elif isinstance(value, dict):
                # Dict of models (e.g., file_map)
                serialized[key] = {
                    k: v.dict() if hasattr(v, "dict") else v
                    for k, v in value.items()
                }
            elif isinstance(value, list):
                # List of models (e.g., tasks)
                serialized[key] = [
                    item.dict() if hasattr(item, "dict") else item
                    for item in value
                ]
            else:
                # Primitive types
                serialized[key] = value

        return serialized

    def get_last_completed_task(self) -> Optional[int]:
        """
        Get index of last successfully completed task

        Returns:
            Task index or None
        """
        checkpoints = self.list_checkpoints()
        completed = [
            cp for cp in checkpoints
            if cp.get("tag") == "completed"
        ]

        if completed:
            return max(cp["task_idx"] for cp in completed)

        return None
