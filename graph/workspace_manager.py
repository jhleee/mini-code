import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List


class WorkspaceManager:
    """Manages isolated workspaces for concurrent agent sessions"""

    def __init__(self, base_dir: str = "workspaces"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.sessions_file = self.base_dir / "sessions.json"

    def create_session(self, prd_name: str, session_id: Optional[str] = None) -> Dict[str, str]:
        """Create a new isolated workspace session

        Args:
            prd_name: Name of the PRD (e.g., "calculator")
            session_id: Optional custom session ID

        Returns:
            Dict with session info: {session_id, workspace_path, prd_name, created_at}
        """
        if not session_id:
            # Generate session ID: prd_name + timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = f"{prd_name}_{timestamp}"

        # Create workspace directory
        workspace_path = self.base_dir / session_id
        workspace_path.mkdir(exist_ok=True)

        # Create session metadata
        session_info = {
            "session_id": session_id,
            "workspace_path": str(workspace_path.absolute()),
            "prd_name": prd_name,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }

        # Save to sessions registry
        self._save_session(session_info)

        print(f"[WORKSPACE] Created session: {session_id}")
        print(f"[WORKSPACE] Path: {workspace_path.absolute()}")

        return session_info

    def list_sessions(self, prd_name: Optional[str] = None) -> List[Dict]:
        """List all sessions, optionally filtered by PRD name"""
        sessions = self._load_sessions()

        if prd_name:
            sessions = [s for s in sessions if s.get("prd_name") == prd_name]

        # Sort by creation time (newest first)
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return sessions

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session info by ID"""
        sessions = self._load_sessions()
        for session in sessions:
            if session["session_id"] == session_id:
                return session
        return None

    def get_latest_session(self, prd_name: str) -> Optional[Dict]:
        """Get the most recent session for a PRD"""
        sessions = self.list_sessions(prd_name)
        return sessions[0] if sessions else None

    def complete_session(self, session_id: str, status: str = "complete"):
        """Mark session as complete"""
        sessions = self._load_sessions()
        for session in sessions:
            if session["session_id"] == session_id:
                session["status"] = status
                session["completed_at"] = datetime.now().isoformat()
                break

        self._save_all_sessions(sessions)

    def cleanup_old_sessions(self, days: int = 7):
        """Remove sessions older than N days"""
        from datetime import timedelta

        sessions = self._load_sessions()
        cutoff = datetime.now() - timedelta(days=days)

        removed = []
        kept = []

        for session in sessions:
            created = datetime.fromisoformat(session["created_at"])
            if created < cutoff:
                # Remove workspace directory
                workspace_path = Path(session["workspace_path"])
                if workspace_path.exists():
                    import shutil
                    shutil.rmtree(workspace_path)
                removed.append(session["session_id"])
            else:
                kept.append(session)

        self._save_all_sessions(kept)

        print(f"[WORKSPACE] Cleaned up {len(removed)} old sessions")
        return removed

    def _load_sessions(self) -> List[Dict]:
        """Load sessions from JSON file"""
        if not self.sessions_file.exists():
            return []

        try:
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def _save_session(self, session_info: Dict):
        """Append new session to registry"""
        sessions = self._load_sessions()
        sessions.append(session_info)
        self._save_all_sessions(sessions)

    def _save_all_sessions(self, sessions: List[Dict]):
        """Save all sessions to JSON file"""
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)


def print_session_info(session: Dict):
    """Pretty print session information"""
    print("\n" + "="*60)
    print(f"Session: {session['session_id']}")
    print("="*60)
    print(f"PRD: {session['prd_name']}")
    print(f"Workspace: {session['workspace_path']}")
    print(f"Created: {session['created_at']}")
    print(f"Status: {session.get('status', 'unknown')}")
    if 'completed_at' in session:
        print(f"Completed: {session['completed_at']}")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Demo usage
    manager = WorkspaceManager()

    # Create sessions
    session1 = manager.create_session("calculator")
    session2 = manager.create_session("todo_app")

    # List sessions
    print("\nAll sessions:")
    for s in manager.list_sessions():
        print(f"  - {s['session_id']}: {s['prd_name']} ({s['status']})")

    # Get latest for calculator
    latest = manager.get_latest_session("calculator")
    if latest:
        print_session_info(latest)
