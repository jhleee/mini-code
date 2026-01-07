"""Simple test runner without pytest dependency issues"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from graph.state import AgentState, Subtask, ExecutionResult
from graph.nodes import Retriever, Critic, RepoManager
from graph.nodes.executor import Executor


def test_retriever_no_workspace():
    """Test retriever with no existing workspace"""
    print("Testing Retriever with no workspace...")
    retriever = Retriever(workspace_dir="nonexistent_dir")
    state = {
        "subtasks": [Subtask(task_id=1, description="Create user model")],
        "keywords": ["user", "model"],
        "current_task_idx": 0
    }

    result = retriever(state)
    assert "context" in result
    assert result["status"].startswith("retrieval_complete")
    print("[PASS] Retriever test passed")


def test_critic_success():
    """Test critic with successful execution"""
    print("Testing Critic with success...")
    critic = Critic()
    state = {
        "subtasks": [Subtask(task_id=1, description="Test task")],
        "current_task_idx": 0,
        "retry_count": 0,
        "max_retries": 3,
        "exec_result": ExecutionResult(passed=True, output="Success"),
        "generated_code": "def test(): pass",
        "generated_test": "assert True"
    }

    result = critic(state)
    assert result["current_task_idx"] == 1
    assert result["retry_count"] == 0
    assert state["subtasks"][0].completed is True
    print("[PASS] Critic success test passed")


def test_critic_failure_retry():
    """Test critic with failed execution (should retry)"""
    print("Testing Critic with retry...")
    critic = Critic()
    state = {
        "subtasks": [Subtask(task_id=1, description="Test task")],
        "current_task_idx": 0,
        "retry_count": 0,
        "max_retries": 3,
        "exec_result": ExecutionResult(passed=False, output="", error="Test failed")
    }

    result = critic(state)
    assert result["retry_count"] == 1
    assert result["current_task_idx"] == 0
    print("[PASS] Critic retry test passed")


def test_executor_simple_code():
    """Test executor with simple passing code"""
    print("Testing Executor with simple code...")
    executor = Executor()
    state = {
        "generated_code": "def add(a, b):\n    return a + b",
        "generated_test": "def test_add():\n    assert add(2, 3) == 5"
    }

    result = executor(state)
    if not result["exec_result"].passed:
        print(f"Expected test to pass but it failed:")
        print(f"Output: {result['exec_result'].output}")
        print(f"Error: {result['exec_result'].error}")
    assert result["exec_result"].passed is True
    print("[PASS] Executor test passed")


def test_executor_failing_test():
    """Test executor with failing test"""
    print("Testing Executor with failing test...")
    executor = Executor()
    state = {
        "generated_code": "def add(a, b):\n    return a - b",
        "generated_test": "def test_add():\n    assert add(2, 3) == 5"
    }

    result = executor(state)
    assert result["exec_result"].passed is False
    print("[PASS] Executor failing test passed")


def test_repo_manager_save_files():
    """Test repo manager saves files correctly"""
    print("Testing RepoManager...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_manager = RepoManager(workspace_dir=tmp_dir)
        state = {
            "subtasks": [
                Subtask(
                    task_id=1,
                    description="Create user model",
                    completed=True,
                    code="class User: pass",
                    test_code="def test_user(): pass"
                )
            ]
        }

        result = repo_manager(state)
        assert "final_files" in result
        assert "SUMMARY.md" in result["final_files"]
        print("[PASS] RepoManager test passed")


if __name__ == "__main__":
    print("Running unit tests...\n")
    try:
        test_retriever_no_workspace()
        test_critic_success()
        test_critic_failure_retry()
        test_executor_simple_code()
        test_executor_failing_test()
        test_repo_manager_save_files()
        print("\n[SUCCESS] All tests passed!")
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
