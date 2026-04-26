import os
import logging

try:
    from litellm import completion
except ImportError:
    completion = None
    logging.warning("LiteLLM not installed. Run: pip install litellm")

class LLMRouter:
    """
    Multi-model routing layer utilizing LiteLLM.
    Allows dynamic switching between fast (Gemini) and reasoning (Claude) models.
    """
    
    def __init__(self):
        # Configure API keys from environment
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        
        # Default models
        self.FAST_MODEL = "gemini/gemini-1.5-flash"
        self.REASONING_MODEL = "claude-3-5-sonnet-20241022"

    def execute_prompt(self, messages: list, model_type: str = "fast", **kwargs):
        """
        Routes the prompt to the appropriate model via LiteLLM.
        model_type: 'fast' or 'reasoning'
        """
        if not completion:
            return "LiteLLM not available. Mock response generated."

        model = self.FAST_MODEL if model_type == "fast" else self.REASONING_MODEL
        
        try:
            response = completion(
                model=model,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"LiteLLM routing error: {e}")
            return f"Error executing prompt on {model}: {e}"

# Example Usage
if __name__ == "__main__":
    router = LLMRouter()
    print("Routing to fast model...")
    # res = router.execute_prompt([{"role": "user", "content": "What is IPC-2221?"}], "fast")
