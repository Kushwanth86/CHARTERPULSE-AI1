from services.api.app.repositories.location_repository import LocationRepository


class LocationService:

    def __init__(self):
        self.repository = LocationRepository()

    def list_locations(self) -> list[dict]:
        return self.repository.list_locations()
