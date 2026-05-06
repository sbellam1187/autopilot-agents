"""
Prompt loading utility for autopilot agents.

This module provides functionality to load system prompts from markdown files
instead of having them hardcoded in the agent implementations.
"""

import asyncio
from pathlib import Path
from typing import Dict

def get_prompts_directory() -> Path:
    """Get the path to the prompts directory."""
    # Get the directory where this file is located (utils)
    current_dir = Path(__file__).parent
    # Go up one level to app, then into prompts
    prompts_dir = current_dir.parent / "prompts"
    return prompts_dir

async def load_prompt(agent_name: str) -> str:
    """
    Load a system prompt from a markdown file.
    
    Args:
        agent_name: Name of the agent (e.g., 'azure_agent', 'caas_agent')
        
    Returns:
        The prompt content as a string
        
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
        IOError: If there's an error reading the file
    """
    prompts_dir = get_prompts_directory()
    prompt_file = prompts_dir / f"{agent_name}.md"
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    
    try:
        # Use asyncio.to_thread for non-blocking file reading
        def read_file_sync():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        
        content = await asyncio.to_thread(read_file_sync)
        return content
    except IOError as e:
        raise IOError(f"Error reading prompt file {prompt_file}: {e}")

async def format_prompt(agent_name: str, **kwargs) -> str:
    """
    Load and format a system prompt with provided variables.
    
    Args:
        agent_name: Name of the agent
        **kwargs: Variables to substitute in the prompt template
        
    Returns:
        The formatted prompt content
    """
    template = await load_prompt(agent_name)
    
    # Set default values for common variables if not provided
    defaults = {
        'reasoning_instruction': '',
        'language': 'english'
    }
    
    # Merge defaults with provided kwargs
    format_vars = {**defaults, **kwargs}
    
    try:
        return template.format(**format_vars)
    except KeyError as e:
        raise ValueError(f"Missing required variable in prompt template: {e}")

def list_available_prompts() -> list[str]:
    """
    List all available prompt files.
    
    Returns:
        List of agent names that have prompt files
    """
    prompts_dir = get_prompts_directory()
    if not prompts_dir.exists():
        return []
    
    prompt_files = prompts_dir.glob("*.md")
    return [f.stem for f in prompt_files if f.stem != "README"]

async def validate_prompts() -> Dict[str, bool]:
    """
    Validate that all expected prompts exist and are readable.
    
    Returns:
        Dictionary mapping agent names to their validation status
    """
    expected_agents = [
        'azure_agent',
        'caas_agent', 
        'github_agent',
        'graph_agent',
        'rag_agent',
        'sample_agent',
        'supervisor_agent',
        'supervisor_agent_synthesis'
    ]
    
    results = {}
    for agent in expected_agents:
        try:
            await load_prompt(agent)
            results[agent] = True
        except (FileNotFoundError, IOError):
            results[agent] = False
    
    return results

# For backward compatibility and debugging
if __name__ == "__main__":
    print("Available prompts:", list_available_prompts())
    
    async def main():
        validation_results = await validate_prompts()
        print("Validation results:", validation_results)
    
    asyncio.run(main())
