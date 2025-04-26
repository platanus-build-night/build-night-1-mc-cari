from abc import ABC, abstractmethod
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
import os

class CodeGenerationResponse(BaseModel):
    code: str = Field(description="The generated C++ solution")
    explanation: str = Field(description="Explanation of the solution approach")

class LLMProvider(ABC):
    @abstractmethod
    def get_llm(self):
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, model_name: str = "o3-mini"):
        self.model_name = model_name
        
    def get_llm(self):
        return ChatOpenAI(
            model_name=self.model_name,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        ).with_structured_output(CodeGenerationResponse)

class AnthropicProvider(LLMProvider):
    def __init__(self, model_name: str = "claude-3-7-sonnet-20250219"):
        self.model_name = model_name
        
    def get_llm(self):
        return ChatAnthropic(
            model_name=self.model_name,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        ).with_structured_output(CodeGenerationResponse)

class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str = "gemini-1.5-pro"):
        self.model_name = model_name
        
    def get_llm(self):
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        ).with_structured_output(CodeGenerationResponse)

class DumbProvider(LLMProvider):
    def __init__(self):
        from dumb_generator import DumbCodeGenerator
        self.generator = DumbCodeGenerator()
        
    def get_llm(self):
        return self.generator

def get_provider(model_id: str) -> LLMProvider:
    model_to_provider = {
        "o3-mini": lambda: OpenAIProvider("o3-mini"),
        "o1": lambda: OpenAIProvider("o1"),
        "claude-3-7-sonnet-20250219": lambda: AnthropicProvider("claude-3-7-sonnet-20250219"),
        "gemini-1.5-pro": lambda: GeminiProvider("gemini-1.5-pro")
    }
    
    if model_id not in model_to_provider:
        raise ValueError(f"Unknown model: {model_id}. Available models: {list(model_to_provider.keys())}")
        
    return model_to_provider[model_id]() 