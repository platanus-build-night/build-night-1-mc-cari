import os
from typing import Dict
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from .utils import read_pdf_content, read_limits
from .providers import get_provider, CodeGenerationResponse
from .dumb_generator import DumbCodeGenerator
from .models import Verdict, CodeGenerationRequest, CodeGenerationResponse
load_dotenv()

class CodeGenerator:
    def __init__(self, model_id: str = "o3-mini"):
        logger.info(f"Initializing CodeGenerator with model: {model_id}")
        self.model_id = model_id
        self.provider = get_provider(model_id)
        self.llm = self.provider.get_llm()
        
    def _read_problem_files(self, problem_id: str) -> Dict[str, str]:
        logger.info(f"Reading problem files for: {problem_id}")
        contest_name, problem_letter = problem_id.split("/")
        base_path = os.path.join("Contests", contest_name)
        problem_path = os.path.join(base_path, problem_letter)
        
        # Read problem statement from PDF
        pdf_path = os.path.join(problem_path, "description", f"{problem_letter}.pdf")
        if not os.path.exists(pdf_path):
            logger.error(f"Problem statement PDF not found at {pdf_path}")
            raise Exception(f"Problem statement PDF not found at {pdf_path}")
        
        logger.info("Reading problem statement and limits")
        statement = read_pdf_content(pdf_path)
        limits = read_limits(problem_path)
        logger.info(f"Problem limits: {limits}")
            
        return {
            "statement": statement,
            "time_limit": limits.get("time_limit", 1),
            "memory_limit": limits.get("memory_limit", 128)
        }
        
    def generate_code(self, problem_id: str) -> CodeGenerationResponse:
        logger.info(f"Generating code for problem: {problem_id}")
        problem_data = self._read_problem_files(problem_id)
        
        logger.info("Creating prompt template")
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            Dont add ```cpp or ``` at the beginning or end of the code.
            You are an expert competitive programmer. 
            Generate a C++  solution for the given problem.
            The solution should be efficient and handle all edge cases.
            The explanation should be short and concise. With one paragraph.
             
            IMPORTANT: Return the response in this exact format:
            {{
                "code": str,  # The raw C++ code without any markdown or formatting
                "explanation": str  # A short explanation of the solution approach
            }}
            
            Example response:
            {{
                "code": "#include<bits/stdc++.h> using namespace std;int main() {{    int n;    cin >> n;    cout << n * 2;    return 0;}}",
                "explanation": "Double the input number."
            }}
            
            The code requires the following things:
            - Don't comment the code, just write the code.
            - Follow the best competitive programming practices.
            - Do not use any markdown formatting or code blocks.
            - The code should be ready to compile and run.
            - Return a valid JSON object with "code" and "explanation" fields.
            - Use the standard library #include<bits/stdc++.h>

            Time limit: {time_limit} seconds
            Memory limit: {memory_limit} MB"""),
            ("user", "Problem statement:\n{statement}")
        ])
        
        logger.info("Invoking LLM with prompt")
        chain = prompt | self.llm
        
        try:
            result = chain.invoke({
                "statement": problem_data["statement"],
                "time_limit": problem_data["time_limit"],
                "memory_limit": problem_data["memory_limit"]
            })
            logger.info("Successfully generated code")
            return result
        except Exception as e:
            logger.error(f"Error generating code: {str(e)}", exc_info=True)
            raise 