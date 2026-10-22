import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


logger = logging.getLogger(__name__)

FREIGHTOS_URL = "https://ship.freightos.com/api/shippingCalculator"

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
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            # Log only the status and category; never log the request URL or headers.
            logger.warning(
                "Freightos upstream HTTP error: status=%s",
                exc.code,
            )
            raise FreightosServiceError(
                "Freightos is temporarily unavailable."
            ) from exc
        except URLError as exc:
            reason = exc.reason
            logger.warning(
                "Freightos upstream connection error: reason_type=%s",
                type(reason).__name__,
            )
            raise FreightosServiceError(
                "Freightos is temporarily unavailable."
            ) from exc
        except (TimeoutError, OSError) as exc:
            logger.warning(
                "Freightos upstream network error: error_type=%s",
                type(exc).__name__,
            )
            raise FreightosServiceError(
                "Freightos is temporarily unavailable."
            ) from exc
        except (ValueError, UnicodeDecodeError) as exc:
            logger.warning(
                "Freightos returned invalid JSON: error_type=%s",
                type(exc).__name__,
            )
            raise FreightosServiceError(
                "Freightos returned invalid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise FreightosServiceError("Unexpected response from Freightos.")

        body = payload.get("response", {})
        if not isinstance(body, dict):
            raise FreightosServiceError("Unexpected response from Freightos.")

        if body.get("errors"):
            raise FreightosServiceError(
                "Freightos could not estimate this shipment."
            )

        estimates = body.get("estimatedFreightRates")
        if not isinstance(estimates, dict):
            raise FreightosServiceError(
                "No freight estimate is available for this route."
            )

        # Freightos can return a valid response with zero quotes and no mode.
        if estimates.get("numQuotes") == 0:
            raise FreightosServiceError(
                "No freight quotes are available for this route and container type."
            )

        mode = estimates.get("mode")
        if isinstance(mode, list):
            mode = mode[0] if mode else None

        if not isinstance(mode, dict):
            logger.warning(
                "Freightos response did not contain a usable quote: "
                "num_quotes=%s",
                estimates.get("numQuotes", "unknown"),
            )
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
            logger.warning(
                "Freightos returned an invalid price range: error_type=%s",
                type(exc).__name__,
            )
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
