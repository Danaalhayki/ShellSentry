"""Application-wide service singletons (SSH, LLM, validator, RAG, logging)."""

from .security import SecurityLayer
from .llm_client import LLMClient
from .command_validator import CommandValidator
from .ssh_executor import SSHExecutor
from .logger import setup_logger
from .rag_pipeline import RagPipeline

security_layer = SecurityLayer()
llm_client = LLMClient()
command_validator = CommandValidator()
ssh_executor = SSHExecutor()
rag_pipeline = RagPipeline()
logger = setup_logger()
