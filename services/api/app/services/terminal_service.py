from services.api.app.repositories.terminal_repository import TerminalRepository


class TerminalService:

    def __init__(self):
        self.repository = TerminalRepository()

    def list_terminals(self) -> list[dict]:
        return self.repository.list_terminals()
