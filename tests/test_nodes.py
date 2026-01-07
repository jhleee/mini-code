import pytest
from graph.state import AgentState, Subtask, ExecutionResult
from graph.nodes import Retriever, Critic, RepoManager
from graph.nodes.executor import Executor


class TestRetriever:
    def test_retriever_no_workspace(self):
        """Test retriever with no existing workspace"""
        retriever = Retriever(workspace_dir="nonexistent_dir")
        state = {
            "subtasks": [Subtask(task_id=1, description="Create user model")],
            "keywords": ["user", "model"],
            "current_task_idx": 0
        }

        result = retriever(state)
        assert "context" in result
        assert result["status"].startswith("retrieval_complete")


class TestCritic:
    def test_critic_success(self):
        """Test critic with successful execution"""
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
        assert result["current_task_idx"] == 1  # Move to next task
        assert result["retry_count"] == 0  # Reset retry count
        assert state["subtasks"][0].completed is True

    def test_critic_failure_retry(self):
        """Test critic with failed execution (should retry)"""
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
        assert result["current_task_idx"] == 0  # Stay on same task

    def test_critic_max_retries(self):
        """Test critic when max retries reached"""
        critic = Critic()
        state = {
            "subtasks": [Subtask(task_id=1, description="Test task")],
            "current_task_idx": 0,
            "retry_count": 3,
            "max_retries": 3,
            "exec_result": ExecutionResult(passed=False, output="", error="Test failed")
        }

        result = critic(state)
        assert result["current_task_idx"] == 1  # Skip to next task
        assert state["subtasks"][0].completed is False


class TestExecutor:
    def test_executor_simple_code(self):
        """Test executor with simple passing code"""
        executor = Executor()
        state = {
            "generated_code": "def add(a, b):\n    return a + b",
            "generated_test": "def test_add():\n    assert add(2, 3) == 5"
        }

        result = executor(state)
        assert result["exec_result"].passed is True
        assert "test_add passed" in result["exec_result"].output

    def test_executor_failing_test(self):
        """Test executor with failing test"""
        executor = Executor()
        state = {
            "generated_code": "def add(a, b):\n    return a - b",  # Wrong implementation
            "generated_test": "def test_add():\n    assert add(2, 3) == 5"
        }

        result = executor(state)
        assert result["exec_result"].passed is False


class TestRepoManager:
    def test_repo_manager_save_files(self, tmp_path):
        """Test repo manager saves files correctly"""
        repo_manager = RepoManager(workspace_dir=str(tmp_path))
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
        assert len(result["final_files"]) >= 1  # At least SUMMARY.md
        assert "SUMMARY.md" in result["final_files"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
