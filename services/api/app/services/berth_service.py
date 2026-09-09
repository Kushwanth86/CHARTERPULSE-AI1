from services.api.app.repositories.berth_repository import BerthRepository


class BerthService:

    def __init__(self):
        self.repository = BerthRepository()

    def list_berths(self) -> list[dict]:
        return self.repository.list_berths()
