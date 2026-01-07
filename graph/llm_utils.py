"""
LLM Utilities - Reasoning model support and response processing

Handles <think> tags from reasoning models and provides clean response extraction.
Logs reasoning traces and execution history to workspace.
"""
import re
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI


def remove_think_tags(text: str) -> str:
    """
    Remove <think>...</think> tags from reasoning model output.

    Reasoning models (like deepseek-reasoner, o1, etc.) output internal reasoning
    within <think> tags. This should be stripped before parsing the actual response.

    Args:
        text: Raw LLM response text

    Returns:
        Clean text with <think> tags removed
    """
    if not text:
        return text

    # Remove <think>...</think> blocks (non-greedy, multiline)
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Also handle self-closing <think/> tags
    cleaned = re.sub(r'<think\s*/>', '', cleaned, flags=re.IGNORECASE)

    # Clean up extra whitespace
    cleaned = cleaned.strip()

    return cleaned


def extract_response_content(response) -> str:
    """
    Extract clean content from LLM response, handling reasoning models.

    Args:
        response: LangChain AIMessage or similar response object

    Returns:
        Clean response content with <think> tags removed
    """
    if hasattr(response, 'content'):
        content = response.content
    elif isinstance(response, str):
        content = response
    else:
        content = str(response)

    return remove_think_tags(content)


def create_llm_from_env() -> ChatOpenAI:
    """
    Create ChatOpenAI instance from environment variables.

    Environment variables:
        LLM_BASE_URL: API endpoint URL
        LLM_API_KEY: API key (default: "dummy")
        LLM_MODEL: Model name (default: "gpt-4o")
        LLM_TEMPERATURE: Temperature (default: 0.7)

    Returns:
        Configured ChatOpenAI instance
    """
    base_url = os.getenv("LLM_BASE_URL", "https://82c2209d4a22.ngrok-free.app/v1")
    api_key = os.getenv("LLM_API_KEY", "dummy")
    model = os.getenv("LLM_MODEL", "gpt-4o")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    print(f"[LLM] Initializing with base_url={base_url}, model={model}")

    return ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature
    )


def is_reasoning_model(model_name: str) -> bool:
    """
    Check if model is a reasoning model that uses <think> tags.

    Args:
        model_name: Model identifier

    Returns:
        True if model is known to use reasoning tags
    """
    reasoning_patterns = [
        'deepseek-reasoner',
        'o1-preview',
        'o1-mini',
        'o3',
        'reasoner',
        'thinking'
    ]

    model_lower = model_name.lower()
    return any(pattern in model_lower for pattern in reasoning_patterns)


def extract_think_content(text: str) -> Optional[str]:
    """
    Extract reasoning content from <think> tags.

    Args:
        text: Raw LLM response text

    Returns:
        Content inside <think> tags, or None if not found
    """
    if not text:
        return None

    # Extract <think>...</think> content (non-greedy, multiline)
    match = re.search(r'<think>(.*?)</think>', text, flags=re.DOTALL | re.IGNORECASE)

    if match:
        return match.group(1).strip()

    return None


def log_llm_interaction(
    workspace_dir: str,
    node_name: str,
    prompt: str,
    response: str,
    reasoning_trace: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log LLM interaction to workspace logs directory.

    Creates logs in: {workspace_dir}/logs/{node_name}_{timestamp}.json

    Args:
        workspace_dir: Workspace directory path
        node_name: Name of the node (e.g., "planner", "code_writer")
        prompt: Prompt sent to LLM
        response: Clean response (without <think> tags)
        reasoning_trace: Content from <think> tags (if reasoning model)
        metadata: Additional metadata to log
    """
    # Create logs directory
    logs_dir = Path(workspace_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Capture timestamp once for consistency
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
    timestamp_iso = now.isoformat()

    # Create log entry
    log_file = logs_dir / f"{node_name}_{timestamp}.json"

    log_entry = {
        "timestamp": timestamp_iso,
        "node": node_name,
        "prompt": prompt,
        "response": response,
        "reasoning_trace": reasoning_trace,
        "metadata": metadata or {}
    }

    # Write log
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_entry, f, indent=2, ensure_ascii=False)

    # Also append to session log for sequential reading
    session_log = logs_dir / "session.log"
    with open(session_log, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"[{timestamp_iso}] {node_name.upper()}\n")
        f.write(f"{'='*80}\n\n")

        if reasoning_trace:
            f.write(f"=== REASONING TRACE ===\n{reasoning_trace}\n\n")

        f.write(f"=== PROMPT ===\n{prompt[:500]}...\n\n")
        f.write(f"=== RESPONSE ===\n{response[:500]}...\n\n")

        if metadata:
            f.write(f"=== METADATA ===\n{json.dumps(metadata, indent=2)}\n\n")

    print(f"[LOG] {node_name} interaction logged to {log_file.name}")
    if reasoning_trace:
        print(f"[LOG] Reasoning trace captured ({len(reasoning_trace)} chars)")


def log_execution(workspace_dir: str, node_name: str, state_update: Dict[str, Any]):
    """
    Log node execution and state updates.

    Creates logs in: {workspace_dir}/logs/execution.log

    Args:
        workspace_dir: Workspace directory path
        node_name: Name of the node
        state_update: State changes made by the node
    """
    logs_dir = Path(workspace_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Capture timestamp once for consistency
    timestamp_iso = datetime.now().isoformat()

    execution_log = logs_dir / "execution.log"

    with open(execution_log, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"[{timestamp_iso}] NODE: {node_name}\n")
        f.write(f"{'='*60}\n")

        # Log key state changes
        for key, value in state_update.items():
            if key in ["status", "current_task_idx", "retry_count"]:
                f.write(f"{key}: {value}\n")
            elif key == "feedback" and value:
                f.write(f"feedback: {value.dict() if hasattr(value, 'dict') else value}\n")
            elif key in ["generated_code", "generated_test"]:
                f.write(f"{key}: {len(value) if value else 0} chars\n")
            elif key == "file_map":
                f.write(f"file_map: {len(value)} files\n")

        f.write("\n")

    print(f"[LOG] {node_name} execution logged")
