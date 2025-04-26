from enum import Enum
from typing import Optional, List, Dict, Union
from pydantic import BaseModel

class ModelType(str, Enum):
    O3_MINI = "o3-mini"
    CLAUDE_3_7_SONNET = "claude-3-7-sonnet-20250219"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    O1 = "o1"

class VerdictStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    ACCEPTED = "ACCEPTED"
    WRONG_ANSWER = "WRONG_ANSWER"
    TIME_LIMIT = "TIME_LIMIT"
    MEMORY_LIMIT = "MEMORY_LIMIT"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    RUNTIME_ERROR_SIGSEGV = "RUNTIME_ERROR_SIGSEGV"
    RUNTIME_ERROR_SIGXFSZ = "RUNTIME_ERROR_SIGXFSZ"
    RUNTIME_ERROR_SIGFPE = "RUNTIME_ERROR_SIGFPE"
    RUNTIME_ERROR_SIGABRT = "RUNTIME_ERROR_SIGABRT"
    RUNTIME_ERROR_NZEC = "RUNTIME_ERROR_NZEC"
    RUNTIME_ERROR_OTHER = "RUNTIME_ERROR_OTHER"
    OTHER = "OTHER"

class TestCaseResult(BaseModel):
    test_case: str
    expected_output: str
    actual_output: str
    verdict: VerdictStatus

    def __init__(self, **data):
        super().__init__(**data)
        self.test_case = self.test_case[:60] + "..." if len(self.test_case) > 60 else self.test_case
        self.expected_output = self.expected_output[:60] + "..." if len(self.expected_output) > 60 else self.expected_output
        self.actual_output = self.actual_output[:60] + "..." if len(self.actual_output) > 60 else self.actual_output

class Verdict(BaseModel):
    status: VerdictStatus
    test_cases: List[TestCaseResult]
    error_message: Optional[str] = None

    @classmethod
    def from_judge0_status(cls, status_id: int, test_cases: List[TestCaseResult] = None, error_message: str = None) -> 'Verdict':
        if test_cases is None:
            test_cases = []
            
        if status_id in [1, 2]:  # In Queue or Processing
            return cls(status=VerdictStatus.QUEUED, test_cases=test_cases)
        elif status_id == 3:  # Accepted
            return cls(status=VerdictStatus.ACCEPTED, test_cases=test_cases)
        elif status_id == 4:  # Wrong Answer
            return cls(status=VerdictStatus.WRONG_ANSWER, test_cases=test_cases)
        elif status_id == 5:  # Time Limit Exceeded
            return cls(status=VerdictStatus.TIME_LIMIT, test_cases=test_cases)
        elif status_id == 6:  # Compilation Error
            return cls(status=VerdictStatus.COMPILATION_ERROR, test_cases=test_cases, error_message=error_message)
        elif status_id == 7:  # Runtime Error (SIGSEGV)
            return cls(status=VerdictStatus.RUNTIME_ERROR_SIGSEGV, test_cases=test_cases)
        elif status_id == 8:  # Runtime Error (SIGXFSZ)
            return cls(status=VerdictStatus.RUNTIME_ERROR_SIGXFSZ, test_cases=test_cases)
        elif status_id == 9:  # Runtime Error (SIGFPE)
            return cls(status=VerdictStatus.RUNTIME_ERROR_SIGFPE, test_cases=test_cases)
        elif status_id == 10:  # Runtime Error (SIGABRT)
            return cls(status=VerdictStatus.RUNTIME_ERROR_SIGABRT, test_cases=test_cases)
        elif status_id == 11:  # Runtime Error (NZEC)
            return cls(status=VerdictStatus.RUNTIME_ERROR_NZEC, test_cases=test_cases)
        elif status_id == 12:  # Runtime Error (Other)
            return cls(status=VerdictStatus.RUNTIME_ERROR_OTHER, test_cases=test_cases)
        elif status_id == 17:  # Memory Limit Exceeded
            return cls(status=VerdictStatus.MEMORY_LIMIT, test_cases=test_cases)
        else:
            return cls(status=VerdictStatus.OTHER, test_cases=test_cases, error_message=error_message)

class CodeGenerationRequest(BaseModel):
    contestant_id: str
    model: ModelType
    problem_id: str
    leaderboard: Dict[str, Dict[str, Union[str, int]]]

class CodeGenerationResponse(BaseModel):
    submission_id: str
    verdict: Verdict 
    error_message: Optional[str] = None
