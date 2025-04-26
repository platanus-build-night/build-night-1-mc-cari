from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import httpx
import traceback
import logging
import asyncio
from typing import Dict, List, Optional
from backend.utils import read_limits, get_test_cases
from backend.models import Verdict, VerdictStatus, TestCaseResult
import base64
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter()

class SubmissionRequest(BaseModel):
    code: str
    problem_id: str

class SubmissionResponse(BaseModel):
    submission_id: str

# Store active submissions and queues
active_submissions = {}
submission_queue = asyncio.Queue()
MAX_WORKERS = 8  # Maximum number of concurrent submissions
worker_tasks: List[asyncio.Task] = []

def clean_code_for_utf8(code: str) -> str:
    """Clean code to ensure it's UTF-8 compatible."""
    # Remove any non-printable characters
    code = ''.join(char for char in code if char.isprintable() or char in '\n\t')
    # Replace any remaining invalid characters with spaces
    return code.encode('utf-8', errors='replace').decode('utf-8')

async def run_test_case(client: httpx.AsyncClient, code: str, input_data: str, expected_output: str, limits: dict, test_num: int) -> TestCaseResult:
    """Run a single test case and return the result."""
    memory_limit_kb = limits.get("memory_limit", 128) * 1000
    memory_limit_kb = min(memory_limit_kb, 512 * 1000)

    # Clean and ensure UTF-8 compatibility
    code = clean_code_for_utf8(code)
    input_data = clean_code_for_utf8(input_data) if input_data else ""
    expected_output = clean_code_for_utf8(expected_output) if expected_output else ""

    judge0_submission = {
        "source_code": code,
        "language_id": 54,  # C++ (GCC 9.2.0)
        "cpu_time_limit": int(limits.get("time_limit", 1)),  
        "memory_limit": memory_limit_kb,  
        "stdin": input_data,
        "expected_output": expected_output
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    response = await client.post(
        "http://localhost:2358/submissions",
        json=judge0_submission,
        headers=headers
    )
    
    if response.status_code != 201:
        logger.error(f"Judge0 submission failed: {response.text}")
        return TestCaseResult(
            test_case=input_data,
            expected_output=expected_output,
            actual_output="",
            verdict=VerdictStatus.OTHER
        )
    
    submission_token = response.json()["token"]
    result = await wait_for_submission(client, submission_token)

    status_id = result.get("status", {}).get("id")
    actual_output = result.get("stdout", "")
    error_message = result.get("stderr", "")

    logger.info(f"verdict: {Verdict.from_judge0_status(status_id).status}")
    logger.info(f"status_id: {status_id}")
    logger.info(f"test_case: {test_num}")

    if Verdict.from_judge0_status(status_id).status == VerdictStatus.ACCEPTED:
        return TestCaseResult(
            test_case=input_data,
            expected_output=expected_output,
            actual_output=actual_output,
            verdict=Verdict.from_judge0_status(status_id).status
        )
    
    return TestCaseResult(
        test_case=input_data,
        expected_output="a",
        actual_output="a",
        verdict=Verdict.from_judge0_status(status_id).status
    )

async def wait_for_submission(client: httpx.AsyncClient, token: str, max_retries: int = 200) -> dict:
    """Wait for submission to complete by polling Judge0 API."""
    for _ in range(max_retries):
        response = await client.get(
            f"http://localhost:2358/submissions/{token}",
            headers={"Accept": "application/json"}
        )
        if response.status_code != 200:
            logger.error(f"Failed to get submission status: {response.text}")

            # return with status id 13
            return {
                "status": {
                    "id": 13
                }
            }
            
        
        result = response.json()
        status_id = result.get("status", {}).get("id")
        
        if status_id in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]:  # Final states
            return result
            
        await asyncio.sleep(0.5)
    
    raise HTTPException(
        status_code=500,
        detail="Submission timed out waiting for result"
    )

async def worker(worker_id: int):
    """Worker process to handle submissions from the queue."""
    logger.info(f"Worker {worker_id} started")
    while True:
        try:
            # Get next submission from queue
            submission_id, code, problem_id = await submission_queue.get()
            logger.info(f"Worker {worker_id} processing submission {submission_id}")
            
            try:
                # Process the submission
                await process_submission(submission_id, code, problem_id)
            except Exception as e:
                logger.error(f"Worker {worker_id} error processing submission {submission_id}: {str(e)}", exc_info=True)
                active_submissions[submission_id] = {
                    "status": "ERROR",
                    "error": str(e)
                }
            finally:
                submission_queue.task_done()
                
        except Exception as e:
            logger.error(f"Worker {worker_id} error: {str(e)}", exc_info=True)
            await asyncio.sleep(1)  # Prevent tight loop on error

async def process_submission(submission_id: str, code: str, problem_id: str):
    """Process a submission in the background."""
    try:
        active_submissions[submission_id]["status"] = "PROCESSING"
        
        contest_name, problem_letter = problem_id.split("/")
        base_path = os.path.join("Contests", contest_name)
        problem_path = os.path.join(base_path, problem_letter)
        
        # Read limits and test cases
        limits = read_limits(problem_path)
        test_cases = get_test_cases(problem_path)
        
        if not test_cases:
            active_submissions[submission_id] = {
                "status": "COMPLETED",
                "verdict": Verdict(
                    status=VerdictStatus.OTHER,
                    test_cases=[],
                    error_message="No test cases found"
                )
            }
            return
        
        # Run test cases
        async with httpx.AsyncClient() as client:
            test_num = 1
            for input_data, expected_output in test_cases:
                result = await run_test_case(
                    client,
                    code,
                    input_data,
                    expected_output,
                    limits,
                    test_num
                )
                test_num += 1
                if result.verdict != VerdictStatus.ACCEPTED:
                    active_submissions[submission_id] = {
                        "status": "COMPLETED",
                        "verdict": Verdict(
                            status=result.verdict,
                            test_cases=[result]
                        )
                    }
                    return
        
        # If we get here, all tests passed
        active_submissions[submission_id] = {
            "status": "COMPLETED",
            "verdict": Verdict(
                status=VerdictStatus.ACCEPTED,
                test_cases=[]
            )
        }
        
    except Exception as e:
        logger.error(f"Error processing submission {submission_id}: {str(e)}")
        active_submissions[submission_id] = {
            "status": "ERROR",
            "error": str(e)
        }

@router.on_event("startup")
async def startup_event():
    """Start worker tasks on startup."""
    global worker_tasks
    for i in range(MAX_WORKERS):
        task = asyncio.create_task(worker(i))
        worker_tasks.append(task)

@router.on_event("shutdown")
async def shutdown_event():
    """Cancel worker tasks on shutdown."""
    for task in worker_tasks:
        task.cancel()
    await asyncio.gather(*worker_tasks, return_exceptions=True)

@router.post("/submit")
async def submit_code(submission: SubmissionRequest):
    try:
        logger.info(f"Received submission for problem: {submission.problem_id}")
        
        # Generate a unique submission ID
        import uuid
        submission_id = str(uuid.uuid4())
        
        # Store submission info
        active_submissions[submission_id] = {
            "status": "QUEUED",
            "problem_id": submission.problem_id,
            "code": submission.code
        }
        
        # Add to queue for processing
        await submission_queue.put((submission_id, submission.code, submission.problem_id))
        
        return SubmissionResponse(submission_id=submission_id)
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/submit/{submission_id}")
async def get_submission_status(submission_id: str):
    """Get the status of a submission."""
    if submission_id not in active_submissions:
        raise HTTPException(status_code=404, detail="Submission not found")
        
    submission = active_submissions[submission_id]
    
    if submission["status"] == "COMPLETED":
        return submission["verdict"]
    if submission["status"] == "PROCESSING":
        return Verdict(
            status=VerdictStatus.PROCESSING,
            test_cases=[]
        )
    elif submission["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=submission["error"])
    else:
        return {"status": submission["status"]} 