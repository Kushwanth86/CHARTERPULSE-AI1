from services.api.app.intelligence.charter_scenarios import (
    CharterScenarioRequest,
    CharterScenarioResponse,
    calculate_charter_scenarios,
)


class CharterScenarioService:

    def calculate(
        self,
        payload: CharterScenarioRequest,
    ) -> CharterScenarioResponse:
        return calculate_charter_scenarios(payload)
