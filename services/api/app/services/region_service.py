from services.api.app.repositories.region_repository import RegionRepository


class RegionService:

    def __init__(self):
        self.repository = RegionRepository()

    def list_regions(self) -> list[dict]:
        return self.repository.list_regions()
