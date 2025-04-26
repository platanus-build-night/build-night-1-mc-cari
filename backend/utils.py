import os
import json
from PyPDF2 import PdfReader
import subprocess
import logging
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def read_pdf_content(pdf_path: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        raise Exception(f"Error reading PDF file: {str(e)}")

def read_limits(problem_path: str) -> dict:
    limits_path = os.path.join(problem_path, "limits", "cpp")
    if not os.path.exists(limits_path):
        raise Exception(f"Limits file not found at {limits_path}")
        
    try:
        # Execute the limits script and capture its output
        result = subprocess.run(
            ["bash", limits_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the output lines
        lines = result.stdout.strip().split("\n")
        if len(lines) < 3:
            raise Exception("Invalid limits file output format")
            
        return {
            "time_limit": float(lines[0]),  # First line: time limit in seconds
            "memory_limit": float(lines[2]),  # Third line: memory limit in MB
            "repetitions": int(lines[1]),  # Second line: number of repetitions
            "max_file_size": int(lines[3]) if len(lines) > 3 else 1024  # Fourth line: max file size in KB
        }
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to execute limits script: {str(e)}")
    except Exception as e:
        raise Exception(f"Error reading limits: {str(e)}")

def get_test_cases(problem_path: str) -> list:
    """Get all test cases from input/ and output/ folders."""
    test_cases = []
    
    # Get absolute paths
    abs_problem_path = os.path.abspath(problem_path)
    input_dir = os.path.join(abs_problem_path, "input")
    output_dir = os.path.join(abs_problem_path, "output")
    
    if not os.path.exists(input_dir) or not os.path.exists(output_dir):
        return test_cases
        
    for input_file in os.listdir(input_dir):
        # Get the test case number from the input file name
        # Example: F_0001 -> 0001
        test_case_num = input_file.split("_")[-1]
        output_file = input_file
        
        input_path = os.path.join(input_dir, input_file)
        output_path = os.path.join(output_dir, output_file)
        
        if os.path.exists(output_path):
            with open(input_path, "r") as f:
                input_data = f.read()
            with open(output_path, "r") as f:
                output_data = f.read()
            test_cases.append((input_data, output_data))
            
    return test_cases

def read_problem_info(problem_path: str) -> dict:
    """Read problem info from problem.info file."""
    info_path = os.path.join(problem_path, "description", "problem.info")
    if not os.path.exists(info_path):
        return {"name": "Unknown Problem"}
        
    info = {}
    with open(info_path, "r") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                key = key.strip()
                value = value.strip().strip('"')
                if key == "fullname":
                    info["name"] = value
                elif key == "basename":
                    info["letter"] = value
                elif key == "descfile":
                    info["pdf_file"] = value
                
    return info

problem_pool = [
        ("latam2020", "N"),
        ("latam2023", "B"),
        ("latam2023", "D"),
        ("latam2022", "D"),
        ("latam2020", "D"),
        #("latam2022", "I"),
        ("latam2021", "K"),
        #("latam2024", "F"),
    ]

def get_random_problems(num_problems: int = 5) -> list:
    """Get random problems from Contests directory."""
    contests_dir = "Contests"
    all_problems = []
    
    # Collect all problems
    for contest in os.listdir(contests_dir):
        contest_path = os.path.join(contests_dir, contest)
        if os.path.isdir(contest_path):
            for problem in os.listdir(contest_path):
                problem_path = os.path.join(contest_path, problem)
                if os.path.isdir(problem_path):
                    # Check if it's a valid problem directory
                    if os.path.exists(os.path.join(problem_path, "description", "problem.info")):
                        all_problems.append((contest, problem))
    
    # Use only problems in problem_pool, since they are the easiest
    all_problems = problem_pool


    # Select random problems
    selected = random.sample(all_problems, min(num_problems, len(all_problems)))
    
    # Get problem info for each selected problem
    result = []
    for contest, problem in selected:
        problem_path = os.path.join(contests_dir, contest, problem)
        info = read_problem_info(problem_path)
        result.append({
            "problem_id": f"{contest}/{problem}",
            "name": info.get("name", "Unknown Problem")
        })
        
    return result 