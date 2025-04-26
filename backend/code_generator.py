import asyncio
import httpx
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .generator import CodeGenerator
from .dumb_generator import DumbCodeGenerator
from .models import Verdict, CodeGenerationRequest, CodeGenerationResponse, VerdictStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/code_generation", response_model=CodeGenerationResponse)
async def code_generation(request: CodeGenerationRequest):
    logger.info(f"Received code generation request for problem: {request.problem_id} with model: {request.model}")
    try:
        return await handle_code_generation(request)
    except Exception as e:
        logger.error(f"Error in code generation endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def handle_code_generation(request: CodeGenerationRequest) -> CodeGenerationResponse:
    generator = CodeGenerator(model_id=request.model)
    
    try:
        # Generate code
        logger.info("Generating code...")
        result = generator.generate_code(request.problem_id)
        logger.info("Code generation completed")
        
        # Submit code to localhost:8000 with retries
        logger.info("Submitting code...")
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        "http://localhost:8000/api/submit",
                        json={
                            "code": result.code,
                            "problem_id": request.problem_id
                        }
                    )
                    
                    if response.status_code == 200:
                        submission_id = response.json().get("submission_id")
                        logger.info(f"Submission started with ID: {submission_id}")
                        
                        # Wait for submission to complete
                        logger.info("Waiting for submission to complete...")
                        result_dict = await wait_for_submission(client, submission_id)
                        logger.info(f"Raw result: {result_dict}")
                        
                        # Convert dictionary to Verdict object
                        verdict = Verdict(
                            status=VerdictStatus(result_dict.get("status")),
                            test_cases=result_dict.get("test_cases", []),
                            error_message=result_dict.get("error_message")
                        )
                        
                        logger.info(f"Submission completed with verdict: {verdict.status}")
                        
                        return CodeGenerationResponse(
                            submission_id=submission_id,
                            verdict=verdict
                        )
                    else:
                        logger.error(f"Submission failed with status {response.status_code}: {response.text}")
                        return CodeGenerationResponse(
                            submission_id="",
                            verdict=Verdict(
                                status=VerdictStatus.OTHER,
                                test_cases=[],
                            ),
                            error_message=f"Submission failed with status {response.status_code}: {response.text}"
                        )
            except httpx.ConnectTimeout:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection timeout, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Max retries reached, connection timeout")
                    return CodeGenerationResponse(
                        submission_id="",
                        verdict=Verdict(
                            status=VerdictStatus.OTHER,
                            test_cases=[],
                        ),
                        error_message="Connection to submission server timed out after multiple retries. Please ensure the server is running at localhost:8000"
                    )
            except httpx.ConnectError:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection error, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Max retries reached, connection error")
                    return CodeGenerationResponse(
                        submission_id="",
                        verdict=Verdict(
                            status=VerdictStatus.OTHER,
                            test_cases=[],
                        ),
                        error_message="Could not connect to submission server after multiple retries. Please ensure the server is running at localhost:8000"
                    )
                
    except Exception as e:
        logger.error(f"Error in code generation: {str(e)}", exc_info=True)
        return CodeGenerationResponse(
            submission_id="",
            verdict=Verdict(
                status=VerdictStatus.OTHER,
                test_cases=[],
            ),
            error_message=str(e)
        )

async def wait_for_submission(client: httpx.AsyncClient, submission_id: str, max_retries: int = 60) -> dict:
    """Wait for submission to complete by polling."""
    logger.info(f"Waiting for submission {submission_id} to complete...")
    for i in range(max_retries):
        response = await client.get(f"http://localhost:8000/api/submit/{submission_id}")
        if response.status_code == 200:
            result = response.json()
            if result.get("status") != "QUEUED" and result.get("status") != "PROCESSING":
                logger.info(f"Submission {submission_id} completed with status: {result.get('status')}")
                return result
        if i % 10 == 0:  # Log every 10 attempts
            logger.info(f"Still waiting for submission {submission_id}... (attempt {i+1}/{max_retries})")
        await asyncio.sleep(1)
    logger.error(f"Submission {submission_id} timed out after {max_retries} seconds")
    raise TimeoutError("Submission timed out after 60 seconds")

async def test_generation_and_submission():
    # Initialize code generator with desired provider
    dumb_flag = False
    
    generator = CodeGenerator(model_id="gemini-1.5-pro")  # or "openai", "gemini", "dumb", "anthropic"
    if dumb_flag:
        generator = DumbCodeGenerator()
    
    # Generate code for a problem
    problem_id = "latam2020/N"  # Example problem
    try:
        print("Generating code...")
        result = generator.generate_code(problem_id)
        print("Generated Code:")
        print(result.code)
        print("\nExplanation:")
        print(result.explanation)
        
        # Submit to our backend
        print("\nSubmitting code...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/submit",
                json={
                    "code": result.code,
                    "problem_id": problem_id
                }
            )
            
            if response.status_code == 200:
                submission_id = response.json().get("submission_id")
                print(f"Submission started with ID: {submission_id}")
                print("Waiting for submission to complete...")
                
                try:
                    result = await wait_for_submission(client, submission_id)
                    print("\nSubmission Result:")
                    print(f"Status: {result.get('status')}")
                    if result.get('test_cases'):
                        test_case = result['test_cases'][0]
                        print(f"Expected: {test_case.get('expected_output')}")
                        print(f"Actual: {test_case.get('actual_output')}")
                except TimeoutError:
                    print("Submission timed out after 60 seconds")
            else:
                print(f"\nSubmission failed with status {response.status_code}:")
                print(response.text)
                
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        import traceback
        print("Full error traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 