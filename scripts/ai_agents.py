"""
AI Agents Module
================
Implements specialized agents for the product description workflow.
Uses a Writer-Reviewer pattern to ensure high quality and strict formatting.
"""

import os
import json
import logging
from typing import Dict, Optional, Any
from pathlib import Path
from openai import OpenAI

# Setup logging
logger = logging.getLogger("ai_agents")

class BaseAgent:
    """Base class for AI agents handling common API logic."""
    
    def __init__(self, model: str, temperature: float = 0.7):
        self.model = model
        self.temperature = temperature
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=self.api_key)
        self._last_cost = 0.0
        self._last_usage = {"input_tokens": 0, "output_tokens": 0}

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on model pricing."""
        # Pricing per 1M tokens (approximate, update as needed)
        pricing = {
            "gpt-5-nano": {"input": 0.05, "output": 0.15},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
            "gpt-4o": {"input": 2.50, "output": 10.00},
        }
        
        # Default to gpt-4o-mini pricing if unknown
        rates = pricing.get(self.model, pricing["gpt-4o-mini"])
        
        input_cost = (input_tokens / 1_000_000) * rates["input"]
        output_cost = (output_tokens / 1_000_000) * rates["output"]
        return input_cost + output_cost

    def _call_api(self, messages: list, response_format: Optional[dict] = None) -> Optional[str]:
        """Execute the API call with error handling."""
        try:
            api_params = {
                "model": self.model,
                "messages": messages,
            }
            
            # Handle model-specific parameters
            if self.model.startswith("gpt-5"):
                api_params["max_completion_tokens"] = 4000
            else:
                api_params["temperature"] = self.temperature
                api_params["max_tokens"] = 2000
            
            if response_format and not self.model.startswith("gpt-5"):
                api_params["response_format"] = response_format

            response = self.client.chat.completions.create(**api_params)
            content = response.choices[0].message.content
            
            if content is None:
                logger.error(f"API returned None content for {self.model}. Finish reason: {response.choices[0].finish_reason}")
                logger.error(f"Full response: {response}")
            else:
                logger.warning(f"API returned content length: {len(content)}")
                if len(content) < 100:
                    logger.warning(f"Content snippet: {content}")
            
            # Track usage
            if response.usage:
                self._last_usage = {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                }
                self._last_cost = self.calculate_cost(
                    self._last_usage["input_tokens"], 
                    self._last_usage["output_tokens"]
                )
            
            return content

        except Exception as e:
            logger.error(f"API call failed for {self.model}: {e}")
            return None

    @property
    def last_cost(self) -> float:
        return self._last_cost


class WriterAgent(BaseAgent):
    """
    Specialized agent for generating creative product descriptions.
    Uses 'Golden Examples' for few-shot prompting.
    """
    
    def __init__(self, model: str, system_prompt_path: Path, task_prompt_path: Path):
        super().__init__(model, temperature=0.7)
        self.system_prompt = self._load_prompt(system_prompt_path)
        self.task_template = self._load_prompt(task_prompt_path)

    def _load_prompt(self, path: Path) -> str:
        try:
            return path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to load prompt from {path}: {e}")
            return ""

    def generate(self, product_data: Dict[str, Any], golden_example: Optional[Dict] = None) -> Optional[str]:
        """
        Generate draft description.
        
        Args:
            product_data: Dictionary of product attributes.
            golden_example: Optional dictionary with 'input' (user prompt) and 'output' (ideal response) for few-shot.
        """
        # Format the user prompt
        user_prompt = self.task_template.format(**product_data)
        
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Inject Golden Example if available (Few-Shot)
        if golden_example:
            messages.append({"role": "user", "content": golden_example['input']})
            messages.append({"role": "assistant", "content": golden_example['output']})
            
        messages.append({"role": "user", "content": user_prompt})
        
        return self._call_api(messages, response_format={"type": "json_object"})


class ReviewerAgent(BaseAgent):
    """
    Specialized agent for validating and fixing JSON output.
    Enforces strict formatting rules.
    """
    
    def __init__(self, model: str, system_prompt_path: Path):
        super().__init__(model, temperature=0.2) # Low temp for strict validation
        self.system_prompt = self._load_prompt(system_prompt_path)

    def _load_prompt(self, path: Path) -> str:
        try:
            return path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to load prompt from {path}: {e}")
            return ""

    def review(self, draft_content: str) -> Optional[str]:
        """
        Review and fix the draft content.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Review and fix this JSON:\n\n{draft_content}"}
        ]
        
        return self._call_api(messages, response_format={"type": "json_object"})
