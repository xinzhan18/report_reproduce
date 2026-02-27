"""
LLMService - Standardized LLM calling interface

Provides:
- Unified LLM calling with consistent interface
- Automatic retry logic with exponential backoff
- JSON response parsing
- Model name resolution
- Token usage tracking
"""

from typing import Union, Dict, Any, Optional
import json
import time
import logging
import re

from config.llm_config import get_model_name


class LLMService:
    """
    Standardized service for LLM API calls.

    Features:
    - Automatic retry with exponential backoff
    - JSON extraction from responses
    - System prompt management
    - Model selection
    - Error handling
    """

    def __init__(
        self,
        llm_client,
        default_system_prompt: str = "",
        max_retries: int = 3
    ):
        """
        Initialize LLM service.

        Args:
            llm_client: Anthropic API client
            default_system_prompt: Default system prompt for all calls
            max_retries: Maximum retry attempts for failed calls
        """
        self.llm = llm_client
        self.system_prompt = default_system_prompt
        self.max_retries = max_retries
        self.logger = logging.getLogger("llm_service")
        self.total_tokens_used = 0

    def update_system_prompt(self, new_prompt: str):
        """
        Update the system prompt.

        Args:
            new_prompt: New system prompt text
        """
        self.system_prompt = new_prompt

    def call(
        self,
        prompt: str,
        model: str = "sonnet",
        max_tokens: int = 4000,
        temperature: float = 0.7,
        response_format: str = "text",
        system_prompt: Optional[str] = None
    ) -> Union[str, Dict]:
        """
        Call LLM with standard interface.

        Args:
            prompt: User prompt
            model: Model name ("sonnet", "haiku", "opus")
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            response_format: "text" or "json"
            system_prompt: Override system prompt (uses default if None)

        Returns:
            Text response or parsed JSON dict

        Raises:
            Exception if all retries fail
        """
        model_id = get_model_name(model)
        effective_system_prompt = system_prompt or self.system_prompt

        self.logger.info(f"Calling {model} model (max_tokens={max_tokens}, temp={temperature})")

        try:
            response = self.llm.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                system=effective_system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )

            # Track token usage
            if hasattr(response, 'usage'):
                tokens_used = response.usage.input_tokens + response.usage.output_tokens
                self.total_tokens_used += tokens_used
                self.logger.info(f"Tokens used: {tokens_used} (total: {self.total_tokens_used})")

            # Extract text
            text = response.content[0].text

            # Parse JSON if requested
            if response_format == "json":
                return self._extract_json(text)

            return text

        except Exception as e:
            self.logger.error(f"LLM call failed: {str(e)}")
            raise

    def call_with_retry(
        self,
        prompt: str,
        model: str = "sonnet",
        max_tokens: int = 4000,
        temperature: float = 0.7,
        response_format: str = "text",
        system_prompt: Optional[str] = None
    ) -> Union[str, Dict]:
        """
        Call LLM with automatic retry on failure.

        Implements exponential backoff: 1s, 2s, 4s, 8s, ...

        Args:
            Same as call()

        Returns:
            LLM response (text or JSON)

        Raises:
            Exception if all retries exhausted
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return self.call(
                    prompt=prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format=response_format,
                    system_prompt=system_prompt
                )

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All {self.max_retries} retry attempts exhausted")

        raise last_error

    def _extract_json(self, text: str) -> Dict:
        """
        Extract JSON from LLM response.

        Handles responses with or without markdown code blocks.

        Args:
            text: LLM response text

        Returns:
            Parsed JSON dict

        Raises:
            ValueError if JSON parsing fails
        """
        # Try to find JSON in code blocks first
        json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
            else:
                json_text = text

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            self.logger.error(f"Response text: {text[:500]}...")
            raise ValueError(f"Failed to parse JSON from LLM response: {e}")

    def batch_call(
        self,
        prompts: list[str],
        model: str = "sonnet",
        max_tokens: int = 4000,
        temperature: float = 0.7,
        response_format: str = "text"
    ) -> list[Union[str, Dict]]:
        """
        Call LLM multiple times sequentially.

        Note: This is sequential, not parallel (for now).
        Future: Implement parallel batching for better performance.

        Args:
            prompts: List of prompts
            model: Model name
            max_tokens: Max tokens per call
            temperature: Sampling temperature
            response_format: "text" or "json"

        Returns:
            List of responses (same order as prompts)
        """
        self.logger.info(f"Batch processing {len(prompts)} prompts...")
        responses = []

        for i, prompt in enumerate(prompts, 1):
            self.logger.info(f"Processing prompt {i}/{len(prompts)}...")
            response = self.call_with_retry(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=response_format
            )
            responses.append(response)

        return responses

    def get_token_usage(self) -> int:
        """
        Get total tokens used by this service instance.

        Returns:
            Total token count
        """
        return self.total_tokens_used

    def reset_token_count(self):
        """Reset token usage counter."""
        self.total_tokens_used = 0
