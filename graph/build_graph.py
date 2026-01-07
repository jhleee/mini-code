from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
import os

from graph.state import AgentState
from graph.nodes.planner import Planner
from graph.nodes.retriever import Retriever
from graph.nodes.code_writer import CodeWriter
from graph.nodes.file_builder import FileBuilder
from graph.nodes.static_checker import StaticChecker
from graph.nodes.executor import Executor
from graph.nodes.critic import Critic
from graph.nodes.test_generator import TestGenerator
from graph.nodes.repo_manager import RepoManager
from graph.llm_utils import create_llm_from_env


def should_continue_after_critic(state: AgentState) -> str:
    """Routing logic after critic evaluation"""
    current_idx = state.get("current_task_idx", 0)
    total_tasks = len(state.get("tasks", []))

    print(f"[ROUTING] current_task_idx={current_idx}, total_tasks={total_tasks}")

    # If all tasks completed, generate tests
    if current_idx >= total_tasks:
        print(f"[ROUTING] All tasks complete, generating tests")
        return "test_gen"

    # Continue to next task
    print(f"[ROUTING] Continuing to task {current_idx}")
    return "retrieve"


def should_execute_after_static_check(state: AgentState) -> str:
    """
    Routing logic after static check (Phase 3: Code-Then-Execute)

    If static check passed → execute
    If static check failed → write (retry)
    """
    status = state.get("status", "")

    if status == "static_check_passed":
        print(f"[ROUTING] Static check passed → execute")
        return "execute"
    elif status == "static_check_failed":
        print(f"[ROUTING] Static check failed → retry code_writer")
        return "write"
    else:
        # Fallback: continue to execute
        print(f"[ROUTING] Unknown status '{status}', defaulting to execute")
        return "execute"


def build_agent(
    base_url: str = None,
    api_key: str = None,
    model: str = None,
    workspace_dir: str = "workspace"
) -> StateGraph:
    """Build the file-centric coding agent

    Args:
        base_url: LLM endpoint URL (overrides env var)
        api_key: API key for LLM (overrides env var)
        model: Model name (overrides env var)
        workspace_dir: Directory for session workspace
    """

    # Initialize LLM - prefer environment variables
    if base_url or api_key or model:
        # Use provided parameters (backward compatibility)
        # Require base_url from env if not provided
        final_base_url = base_url or os.getenv("LLM_BASE_URL")
        if not final_base_url:
            raise ValueError(
                "LLM_BASE_URL must be provided either as argument or environment variable. "
                "Set LLM_BASE_URL environment variable or pass base_url parameter."
            )

        llm = ChatOpenAI(
            base_url=final_base_url,
            api_key=api_key or os.getenv("LLM_API_KEY", "dummy"),
            model=model or os.getenv("LLM_MODEL", "gpt-4o"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7"))
        )
        print(f"[LLM] Initialized with base_url={llm.base_url}, model={llm.model_name}")
    else:
        # Use environment variables exclusively
        llm = create_llm_from_env()

    # Initialize nodes with session-specific workspace
    planner = Planner(llm, workspace_dir)
    retriever = Retriever(workspace_dir)
    code_writer = CodeWriter(llm, workspace_dir)
    file_builder = FileBuilder()
    static_checker = StaticChecker()  # Phase 3: Code-Then-Execute gate
    executor = Executor(workspace_dir)
    critic = Critic(workspace_dir)  # Phase 3: Checkpoint support
    test_generator = TestGenerator(llm, workspace_dir)
    repo_manager = RepoManager(workspace_dir)

    # Build graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("plan", planner)
    graph.add_node("retrieve", retriever)
    graph.add_node("write", code_writer)
    graph.add_node("build", file_builder)
    graph.add_node("static_check", static_checker)  # Phase 3: Static analysis gate
    graph.add_node("execute", executor)
    graph.add_node("critic", critic)
    graph.add_node("test_gen", test_generator)
    graph.add_node("save", repo_manager)

    # Add edges
    graph.set_entry_point("plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "write")
    graph.add_edge("write", "build")  # Append to file

    # Phase 3: Code-Then-Execute - Static check before execution
    graph.add_edge("build", "static_check")

    # Conditional routing from static_check
    graph.add_conditional_edges(
        "static_check",
        should_execute_after_static_check,
        {
            "execute": "execute",  # Passed → execute
            "write": "write"       # Failed → retry code_writer
        }
    )

    graph.add_edge("execute", "critic")

    # Conditional routing from critic
    graph.add_conditional_edges(
        "critic",
        should_continue_after_critic,
        {
            "retrieve": "retrieve",  # Next task or retry
            "test_gen": "test_gen"   # All done, generate tests
        }
    )

    graph.add_edge("test_gen", "save")
    graph.add_edge("save", END)

    return graph.compile()
