import asyncio
import logging
import httpx
from .generator import CodeGenerator
from .dumb_generator import DumbCodeGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def wait_for_submission(client, submission_id: str, max_retries: int = 60) -> dict:
    """Wait for submission to complete by polling the API."""
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
    
    generator = CodeGenerator(model_id="o3-mini")  # or "openai", "gemini", "dumb", "anthropic"
    if dumb_flag:
        generator = DumbCodeGenerator()
    
    # Generate code for a problem
    problem_id = "latam2020/N"  # Example problem
    try:
        logger.info("Starting test generation and submission")
        logger.info("Generating code...")
        result = generator.generate_code(problem_id)
        logger.info("Code generation completed")
        print("Generated Code:")
        print(result.code)
        print("\nExplanation:")
        print(result.explanation)
        
        # Submit to our backend
        logger.info("Submitting code...")
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
                logger.info(f"Submission started with ID: {submission_id}")
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
                    logger.error("Submission timed out")
                    print("Submission timed out after 60 seconds")
            else:
                logger.error(f"Submission failed with status {response.status_code}: {response.text}")
                print(f"\nSubmission failed with status {response.status_code}:")
                print(response.text)
                
    except Exception as e:
        logger.error(f"Error in test generation: {str(e)}", exc_info=True)
        print(f"Error occurred: {str(e)}")
        import traceback
        print("Full error traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_generation_and_submission()) 