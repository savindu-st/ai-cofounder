"""LangGraph Checkpointer Setup and Thread Configuration.

Provides memory-backed or persistent state checkpointing for LangGraph
workflow sessions and thread-based routing.
"""

from typing import Dict, Any
from langgraph.checkpoint.memory import MemorySaver

# Default singleton checkpointer for workflow execution
_DEFAULT_CHECKPOINTER = MemorySaver()


def get_checkpointer() -> MemorySaver:
    """Returns the default checkpointer instance."""
    return _DEFAULT_CHECKPOINTER


def get_thread_config(venture_id: str) -> Dict[str, Any]:
    """Generates the LangGraph configuration dictionary for a given venture thread.
    
    Args:
        venture_id: The unique identifier for the venture execution thread.
        
    Returns:
        Dict configured with thread_id under configurable namespace.
    """
    return {
        "configurable": {
            "thread_id": venture_id
        }
    }
