# String Toolkit PRD

## Overview
Create a simple string manipulation toolkit with utility functions for common string operations.

## Features

### 1. String Utilities (string_utils.py)
Basic string manipulation functions:

- `reverse_string(text: str) -> str`: Reverse a string
  - Example: "hello" → "olleh"
  - Handle empty strings gracefully

- `count_vowels(text: str) -> int`: Count vowels (a, e, i, o, u) in a string
  - Case-insensitive
  - Example: "Hello World" → 3

- `is_palindrome(text: str) -> bool`: Check if string is a palindrome
  - Ignore case and spaces
  - Example: "A man a plan a canal Panama" → True

### 2. Text Formatter (formatter.py)
Text formatting utilities:

- `title_case(text: str) -> str`: Convert to title case
  - Example: "hello world" → "Hello World"
  - Handle multiple spaces

- `snake_to_camel(text: str) -> str`: Convert snake_case to camelCase
  - Example: "hello_world_test" → "helloWorldTest"
  - First letter lowercase

- `truncate(text: str, max_length: int, suffix: str = "...") -> str`: Truncate long strings
  - Example: truncate("Hello World", 8) → "Hello..."
  - Don't truncate if already short enough

## Technical Requirements
- Pure Python 3.8+
- No external dependencies
- Type hints for all functions
- Clear docstrings

## Success Criteria
- All functions work correctly with example inputs
- Handle edge cases (empty strings, None, etc.)
- Code is clean and well-documented
