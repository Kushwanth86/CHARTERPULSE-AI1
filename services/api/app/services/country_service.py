from services.api.app.repositories.country_repository import CountryRepository


class CountryService:

    def __init__(self):
        self.repository = CountryRepository()

    def list_countries(self) -> list[dict]:
        return self.repository.list_countries()
