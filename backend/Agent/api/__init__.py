"""
API clients for Agent system
Wrappers around existing services for clean Agent architecture
"""

from .mongodb_client import MongoDBClient
from .vector_client import VectorClient
from .pubmed_client import PubMedClient
from .ollama_agent_client import OllamaAgentClient

__all__ = ['MongoDBClient', 'VectorClient', 'PubMedClient', 'OllamaAgentClient']
