from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List
import logging
from backend.utils import get_random_problems

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter()

class ProblemInfo(BaseModel):
    problem_id: str
    name: str

@router.get("/problems")
async def get_problems(num_problems: int = Query(default=5, ge=1, le=10)) -> List[ProblemInfo]:
    """Get random problems.
    
    Args:
        num_problems: Number of problems to return (1-10)
    """
    try:
        problems = get_random_problems(num_problems)
        
        return problems
    except Exception as e:
        logger.error(f"Error getting problems: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get problems: {str(e)}"
        ) 