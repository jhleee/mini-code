"""
LLM Utilities - Reasoning model support and response processing

Handles <think> tags from reasoning models and provides clean response extraction.
"""
import re
import os
from typing import Optional
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
