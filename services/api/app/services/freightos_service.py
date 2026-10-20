
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FREIGHTOS_URL = (
    "https://ship.freightos.com/api/shippingCalculator"
)

SUPPORTED_LOAD_TYPES = {
    "container20",
    "container40",
    "container40HC",
    "container45",
    "container45HC",
}


class FreightosServiceError(Exception):
    """Raised when Freightos cannot provide a usable estimate."""


class FreightosService:
    def estimate(
        self,
        origin: str,
        destination: str,
        loadtype: str = "container40",
        quantity: int = 1,
        weight: float | None = None,
    ) -> dict:
        if loadtype not in SUPPORTED_LOAD_TYPES:
            raise ValueError("Unsupported container load type.")

        if not origin.strip() or not destination.strip():
            raise ValueError("Origin and destination are required.")

        if quantity < 1 or quantity > 20:
            raise ValueError("Quantity must be between 1 and 20.")

        params = {
            "format": "json",
            "origin": origin.strip(),
            "destination": destination.strip(),
            "loadtype": loadtype,
            "quantity": quantity,
        }

        if weight is not None:
            if weight <= 0:
                raise ValueError("Weight must be greater than zero.")
            params["weight"] = weight

        request = Request(
            f"{FREIGHTOS_URL}?{urlencode(params)}",
            headers={"Accept": "application/json"},
        )

        try:
            with urlopen(request, timeout=15) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise FreightosServiceError(
                "Freightos is temporarily unavailable."
            ) from exc
        except (ValueError, UnicodeDecodeError) as exc:
            raise FreightosServiceError(
                "Freightos returned invalid JSON."
            ) from exc

        body = payload.get("response", {})
        if not isinstance(body, dict):
            raise FreightosServiceError(
                "Unexpected response from Freightos."
            )

        if body.get("errors"):
            raise FreightosServiceError(
                "Freightos could not estimate this shipment."
            )

        estimates = body.get("estimatedFreightRates")
        if not isinstance(estimates, dict):
            raise FreightosServiceError(
                "No freight estimate is available for this route."
            )

        mode = estimates.get("mode")
        if isinstance(mode, list):
            mode = mode[0] if mode else None

        if not isinstance(mode, dict):
            raise FreightosServiceError(
                "No usable freight estimate was returned."
            )

        price = mode.get("price", {})
        minimum = price.get("min", {}).get("moneyAmount", {})
        maximum = price.get("max", {}).get("moneyAmount", {})
        transit = mode.get("transitTimes", {})

        try:
            min_price = float(minimum["amount"])
            max_price = float(maximum["amount"])
            currency = minimum["currency"]

            if max_price < min_price:
                raise ValueError("Invalid price range.")
        except (KeyError, TypeError, ValueError) as exc:
            raise FreightosServiceError(
                "Freightos returned an invalid price range."
            ) from exc

        return {
            "provider": "Freightos",
            "estimate_type": "CONTAINER_FREIGHT_ESTIMATE",
            "origin": origin.strip(),
            "destination": destination.strip(),
            "loadtype": loadtype,
            "quantity": quantity,
            "price_min": min_price,
            "price_max": max_price,
            "currency": currency,
            "transit_days_min": transit.get("min"),
            "transit_days_max": transit.get("max"),
            "mode": mode.get("mode", "FCL"),
            "is_estimate": True,
            "source_url": "https://ship.freightos.com",
        }
