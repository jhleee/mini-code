import os
import sys
import argparse
from pathlib import Path
from graph.build_graph import build_agent
from graph.state import AgentState
from graph.workspace_manager import WorkspaceManager, print_session_info
from graph.checkpoint_manager import CheckpointManager


def load_prd(prd_path: str) -> str:
    """Load PRD content from file"""
    with open(prd_path, 'r', encoding='utf-8') as f:
        return f.read()


def run_agent(
    prd_path: str,
    base_url: str = None,
    session_id: str = None,
    resume: bool = False,
    from_checkpoint: int = None
):
    """
    Run the file-centric coding agent with isolated workspace

    Args:
        prd_path: Path to PRD file
        base_url: LLM endpoint URL (overrides env var)
        session_id: Custom session ID
        resume: Resume latest session
        from_checkpoint: Resume from specific task checkpoint (Phase 3)
    """

    # Extract PRD name from path
    prd_name = Path(prd_path).stem

    # Initialize workspace manager
    ws_manager = WorkspaceManager()

    # Handle session
    if resume and session_id:
        # Resume existing session
        session = ws_manager.get_session(session_id)
        if not session:
            print(f"Error: Session '{session_id}' not found")
            return None
        print(f"[INFO] Resuming session: {session_id}")
    elif resume:
        # Resume latest session for this PRD
        session = ws_manager.get_latest_session(prd_name)
        if not session:
            print(f"Error: No previous session found for '{prd_name}'")
            return None
        print(f"[INFO] Resuming latest session: {session['session_id']}")
    else:
        # Create new session
        session = ws_manager.create_session(prd_name, session_id)

    print_session_info(session)

    # Get workspace path
    workspace_path = session["workspace_path"]

    # Load PRD
    print(f"Loading PRD from: {prd_path}")
    prd_content = load_prd(prd_path)

    # Build agent with session-specific workspace
    # If base_url is not provided, it will use environment variables
    if base_url:
        print(f"Building agent with endpoint: {base_url}")
    else:
        print(f"Building agent with environment variables")
    agent = build_agent(base_url=base_url, workspace_dir=workspace_path)

    # Initialize or restore state (Phase 3: Checkpoint support)
    checkpoint_manager = CheckpointManager(workspace_path)

    if from_checkpoint is not None:
        # Restore from specific checkpoint
        print(f"\n[CHECKPOINT] Attempting to restore from task {from_checkpoint}")
        checkpoint = checkpoint_manager.load_checkpoint(from_checkpoint)

        if checkpoint:
            initial_state = checkpoint_manager.restore_state(checkpoint)
            print(f"[CHECKPOINT] Resuming from task {initial_state.get('current_task_idx', 0)}")
        else:
            print(f"[CHECKPOINT] Failed to load checkpoint, starting fresh")
            initial_state = None
    else:
        initial_state = None

    # Create fresh state if no checkpoint
    if initial_state is None:
        initial_state: AgentState = {
            "user_query": f"Implement this PRD: {prd_name}",
            "prd_content": prd_content,
            "file_map": {},
            "tasks": [],
            "current_task_idx": 0,
            "context": "",
            "generated_code": "",
            "generated_test": "",  # Phase 1: separated test code
            "feedback": None,      # Phase 2: rich feedback
            "exec_result": None,   # backward compatibility
            "retry_context": None, # Phase 3: differentiated error handling
            "retry_count": 0,
            "max_retries": 3,
            "status": "initializing"
        }

    print("\n" + "="*60)
    print(f"Starting Coding Agent - Session: {session['session_id']}")
    print("="*60 + "\n")

    # Run the agent
    try:
        config = {"recursion_limit": 100}
        result = agent.invoke(initial_state, config=config)

        print("\n" + "="*60)
        print("Agent Execution Complete")
        print("="*60)
        print(f"\nStatus: {result.get('status')}")

        # Print file map
        file_map = result.get("file_map", {})
        print(f"\nGenerated {len(file_map)} files:")
        for file_path, file_state in file_map.items():
            if file_state.content:
                print(f"  - {file_path}: {len(file_state.content)} chars, {len(file_state.functions)} functions")

        print(f"\nWorkspace location: {workspace_path}")
        print(f"\nFiles saved:")
        for filename, filepath in result.get("final_files", {}).items():
            print(f"  - {filepath}")

        # Print summary
        if "SUMMARY.md" in result.get("final_files", {}):
            summary_path = result["final_files"]["SUMMARY.md"]
            with open(summary_path, 'r', encoding='utf-8') as f:
                print("\n" + f.read())

        # Mark session as complete
        ws_manager.complete_session(session["session_id"], "complete")

        return result

    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback
        traceback.print_exc()

        # Mark session as failed
        ws_manager.complete_session(session["session_id"], "failed")

        return None


def list_sessions_cmd(prd_name: str = None):
    """List all sessions"""
    ws_manager = WorkspaceManager()
    sessions = ws_manager.list_sessions(prd_name)

    if not sessions:
        print("No sessions found.")
        return

    print(f"\nFound {len(sessions)} session(s):\n")
    for session in sessions:
        status_icon = "[OK]" if session.get("status") == "complete" else "[--]"
        print(f"{status_icon} {session['session_id']}")
        print(f"   PRD: {session['prd_name']}")
        print(f"   Created: {session['created_at']}")
        print(f"   Status: {session.get('status', 'unknown')}")
        print(f"   Path: {session['workspace_path']}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Coding Agent - File-centric with isolated workspaces"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run agent on PRD")
    run_parser.add_argument("prd_path", help="Path to PRD file")
    run_parser.add_argument("--session-id", help="Custom session ID")
    run_parser.add_argument("--resume", action="store_true", help="Resume latest session")
    run_parser.add_argument(
        "--base-url",
        default=None,
        help="LLM endpoint URL (overrides LLM_BASE_URL env var)"
    )
    run_parser.add_argument(
        "--from-checkpoint",
        type=int,
        default=None,
        metavar="TASK_IDX",
        help="Resume from specific task checkpoint (Phase 3: Filesystem Checkpoint)"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List sessions")
    list_parser.add_argument("--prd", help="Filter by PRD name")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean old sessions")
    cleanup_parser.add_argument("--days", type=int, default=7, help="Remove sessions older than N days")

    args = parser.parse_args()

    if args.command == "run":
        if not os.path.exists(args.prd_path):
            print(f"Error: PRD file not found: {args.prd_path}")
            sys.exit(1)

        run_agent(
            args.prd_path,
            base_url=args.base_url,
            session_id=args.session_id,
            resume=args.resume,
            from_checkpoint=args.from_checkpoint
        )

    elif args.command == "list":
        list_sessions_cmd(args.prd)

    elif args.command == "cleanup":
        ws_manager = WorkspaceManager()
        removed = ws_manager.cleanup_old_sessions(args.days)
        print(f"Removed {len(removed)} sessions older than {args.days} days")

    else:
        # Default: run with first argument as PRD path (backward compatibility)
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            prd_path = sys.argv[1]
            if os.path.exists(prd_path):
                run_agent(prd_path)
            else:
                parser.print_help()
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
