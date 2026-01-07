from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from graph.state import AgentState
from graph.nodes.planner import Planner
from graph.nodes.retriever import Retriever
from graph.nodes.code_writer import CodeWriter
from graph.nodes.file_builder import FileBuilder
from graph.nodes.executor import Executor
from graph.nodes.critic import Critic
from graph.nodes.test_generator import TestGenerator
from graph.nodes.repo_manager import RepoManager


def should_continue(state: AgentState) -> str:
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


def build_agent(
    base_url: str = "https://82c2209d4a22.ngrok-free.app/v1",
    api_key: str = "dummy",
    model: str = "gpt-4o",
    workspace_dir: str = "workspace"
) -> StateGraph:
    """Build the file-centric coding agent

    Args:
        base_url: LLM endpoint URL
        api_key: API key for LLM
        model: Model name
        workspace_dir: Directory for session workspace
    """

    # Initialize LLM
    llm = ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=0.7
    )

    # Initialize nodes with session-specific workspace
    planner = Planner(llm)
    retriever = Retriever(workspace_dir)
    code_writer = CodeWriter(llm)
    file_builder = FileBuilder()
    executor = Executor(workspace_dir)
    critic = Critic()
    test_generator = TestGenerator(llm)
    repo_manager = RepoManager(workspace_dir)

    # Build graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("plan", planner)
    graph.add_node("retrieve", retriever)
    graph.add_node("write", code_writer)
    graph.add_node("build", file_builder)
    graph.add_node("execute", executor)
    graph.add_node("critic", critic)
    graph.add_node("test_gen", test_generator)
    graph.add_node("save", repo_manager)

    # Add edges
    graph.set_entry_point("plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "write")
    graph.add_edge("write", "build")  # Append to file
    graph.add_edge("build", "execute")
    graph.add_edge("execute", "critic")

    # Conditional routing from critic
    graph.add_conditional_edges(
        "critic",
        should_continue,
        {
            "retrieve": "retrieve",  # Next task or retry
            "test_gen": "test_gen"   # All done, generate tests
        }
    )

    graph.add_edge("test_gen", "save")
    graph.add_edge("save", END)

    return graph.compile()
