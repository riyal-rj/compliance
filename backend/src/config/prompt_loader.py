from pathlib import Path

import yaml

PROMPTS_ROOT = Path(__file__).resolve().parents[2] / "prompts" / "system"

def load_system_prompt(prompt_name: str, **variables: str) -> str:
    """Load and render a versioned system prompt from the folder"""
    prompt_path = PROMPTS_ROOT / f"{prompt_name}.yaml"
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as prompt_file:
        prompt_config = yaml.safe_load(prompt_file)

    if not isinstance(prompt_config, dict) or not isinstance(prompt_config.get("template"), str):
        raise ValueError(f"Invalid system prompt configuration: {prompt_path}")

    prompt = prompt_config["template"]
    for variable_name, variable_value in variables.items():
        prompt = prompt.replace(f"{{{{{variable_name}}}}}", variable_value)
    return prompt