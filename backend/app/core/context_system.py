from Agent.session_manager import SessionManager
from Agent.context_engineer import ContextEngineer

class ContextSystem:
    """Own session/context services for one application instance."""

    def __init__(self):
        self.session_manager = SessionManager()
        self.context_engineer = ContextEngineer()

context_system = ContextSystem()
