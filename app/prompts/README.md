# Agent System Prompts

This directory contains externalized system prompts for all autopilot agents. These prompts were previously hardcoded within the agent implementations and have been moved to separate markdown files for easier management and modification.

## Overview

The externalization of system prompts provides several benefits:

- **Maintainability**: Prompts can be modified without touching agent code
- **Readability**: Prompts are stored in markdown format for better formatting and documentation
- **Version Control**: Changes to prompts can be tracked separately from code changes
- **Reusability**: Prompts can be shared across different implementations
- **Testing**: Different prompt variations can be easily tested

## Prompt Structure

Each prompt file follows this general structure:

```markdown
# Agent Name System Prompt

[Main agent description and role]

[Specific capabilities and tools available]

[Instructions and guidelines]

## Language Instructions
{reasoning_instruction}
[Additional language-specific instructions]
```

## Template Variables

The prompts support template variable substitution using Python's `.format()` method. Common variables include:

- **`{reasoning_instruction}`** - Dynamic reasoning behavior based on `DISABLE_REASONING` environment variable
- **`{language}`** - Language preference from agent state (default: 'english')

## Usage

### Loading Prompts

Use the `prompt_loader` utility to load and format prompts:

```python
from utils.prompt_loader import format_prompt, load_prompt

# Load and format a prompt with variables
system_content = format_prompt(
    'azure_agent',
    reasoning_instruction=reasoning_instruction,
    language=state.get('language', 'english')
)

# Load raw prompt content
raw_prompt = load_prompt('rag_agent')
```

### Validation

The prompt loader includes validation functionality:

```python
from utils.prompt_loader import validate_prompts, list_available_prompts

# Check all prompts are available and readable
validation_results = validate_prompts()

# List available prompt files
available_prompts = list_available_prompts()
```

## Modifying Prompts

When modifying prompts, consider the following guidelines:

1. **Preserve Template Variables**: Ensure required template variables (`{reasoning_instruction}`, `{language}`, etc.) are maintained
2. **Test Changes**: Validate that prompt changes work correctly with the agent implementation
3. **Maintain Consistency**: Keep similar formatting and structure across related agents
4. **Document Changes**: Update this README if you add new prompts or variables
