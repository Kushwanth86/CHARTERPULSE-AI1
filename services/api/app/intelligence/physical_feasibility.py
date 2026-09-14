from __future__ import annotations

from datetime import datetime, timezone


class PhysicalFeasibilityEngine:
    """Evaluate physical and operational feasibility without inventing data.

    A known violated constraint produces ``INFEASIBLE``.
    A missing required constraint produces ``REVIEW``.
    Only when all required checks are known and pass is the result ``FEASIBLE``.
    """

    @staticmethod
    def _dimension_check(
        vessel_value,
        port_limit,
        label: str,
        reasons: list[str],
    ) -> bool | None:
        if port_limit is None:
            return None
        if vessel_value is None:
            reasons.append(f"{label}: vessel dimension unavailable.")
            return None
        if float(vessel_value) > float(port_limit):
            reasons.append(f"{label}: vessel exceeds port limit.")
            return False
        return True

    @staticmethod
    def _capacity_check(
        vessel_capacity,
        required_quantity,
        port_limit,
        reasons: list[str],
    ) -> bool | None:
        if required_quantity is None or vessel_capacity is None:
            reasons.append("Cargo quantity or vessel cargo capacity is unavailable.")
            return None
        if float(vessel_capacity) < float(required_quantity):
            reasons.append("Vessel cargo capacity is insufficient.")
            return False
        if port_limit is not None and float(vessel_capacity) > float(port_limit):
            reasons.append("Vessel cargo capacity exceeds the port vessel-capacity limit.")
            return False
        return True

    @staticmethod
    def _cargo_compatibility(cargo: dict, vessel: dict, constraints: list[dict | None], reasons: list[str]) -> bool | None:
        cargo_type = str(cargo.get("cargo_type") or "").strip().lower()
        material = str(cargo.get("material") or "").strip().lower()
        ship_type = str(vessel.get("ship_type") or "").strip().lower()

        if not cargo_type and not material:
            reasons.append("Cargo type/material is unavailable for compatibility evaluation.")
            return None
        if not ship_type:
            reasons.append("Vessel ship type is unavailable for compatibility evaluation.")
            return None

        combined = f"{cargo_type} {material}"
        is_liquid = any(term in combined for term in ("crude", "oil", "petroleum", "chemical", "liquid"))
        is_dry_bulk = any(term in combined for term in ("dry_bulk", "dry bulk", "coal", "ore", "grain", "coke", "cement"))
        is_container = any(term in combined for term in ("container", "containerized"))
        is_tanker = "tanker" in ship_type
        is_bulk = any(term in ship_type for term in ("bulk", "bulker"))
        is_container_ship = any(term in ship_type for term in ("container", "containership"))

        if is_liquid and not is_tanker:
            reasons.append("Liquid cargo requires a tanker-compatible vessel type.")
            return False
        if is_dry_bulk and is_tanker:
            reasons.append("Dry-bulk cargo is incompatible with a tanker vessel type.")
            return False
        if is_container and not is_container_ship:
            reasons.append("Containerized cargo requires a container-compatible vessel type.")
            return False

        handling_types = []
        for constraint in constraints:
            if constraint and constraint.get("cargo_handling_types"):
                value = constraint["cargo_handling_types"]
                if isinstance(value, list):
                    handling_types.extend(str(item).strip().lower() for item in value)

        if handling_types:
            candidates = {cargo_type, material}
            candidates.discard("")
            if not any(
                candidate in handling_types
                or any(candidate in supported or supported in candidate for supported in handling_types)
                for candidate in candidates
            ):
                reasons.append("Cargo type/material is not listed as supported by the port handling constraints.")
                return False

        return True

    @staticmethod
    def _delivery_window_check(cargo: dict, reasons: list[str]) -> bool | None:
        latest = cargo.get("latest_delivery")
        if latest is None:
            reasons.append("Delivery deadline unavailable.")
            return None

        try:
            if isinstance(latest, str):
                latest_dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
            else:
                latest_dt = latest
            if latest_dt.tzinfo is None:
                latest_dt = latest_dt.replace(tzinfo=timezone.utc)
            ok = latest_dt > datetime.now(timezone.utc)
        except (TypeError, ValueError):
            reasons.append("Delivery deadline could not be evaluated.")
            return None

        if not ok:
            reasons.append("Latest delivery deadline has already passed.")
        return ok

    def evaluate(
        self,
        cargo: dict,
        vessel: dict,
        origin_constraints: dict | None,
        destination_constraints: dict | None,
    ) -> dict:
        reasons: list[str] = []
        checks: dict = {}

        quantity = cargo.get("quantity_mt")
        capacity = vessel.get("cargo_capacity_mt")

        origin_capacity_limit = (origin_constraints or {}).get("max_vessel_capacity_mt")
        destination_capacity_limit = (destination_constraints or {}).get("max_vessel_capacity_mt")
        capacity_limits = [value for value in (origin_capacity_limit, destination_capacity_limit) if value is not None]
        effective_capacity_limit = min(capacity_limits) if capacity_limits else None

        cargo_capacity_ok = self._capacity_check(
            capacity, quantity, effective_capacity_limit, reasons
        )
        checks["cargo_capacity_mt"] = capacity
        checks["required_cargo_mt"] = quantity
        checks["max_vessel_capacity_mt"] = effective_capacity_limit

        cargo_compatibility_ok = self._cargo_compatibility(
            cargo, vessel, [origin_constraints, destination_constraints], reasons
        )
        checks["cargo_type"] = cargo.get("cargo_type")
        checks["material"] = cargo.get("material")
        checks["ship_type"] = vessel.get("ship_type")

        def evaluate_port(constraints: dict | None, prefix: str) -> dict:
            if not constraints:
                reasons.append(f"{prefix}: physical port constraints unavailable.")
                return {"loa": None, "beam": None, "draft": None, "loading": None, "discharge": None}

            loa = self._dimension_check(vessel.get("loa_m"), constraints.get("max_loa_m"), f"{prefix} LOA", reasons)
            beam = self._dimension_check(vessel.get("beam_m"), constraints.get("max_beam_m"), f"{prefix} beam", reasons)
            draft = self._dimension_check(vessel.get("max_draft_m"), constraints.get("max_draft_m"), f"{prefix} draft", reasons)

            loading = constraints.get("loading_available")
            discharge = constraints.get("discharge_available")
            if loading is False:
                reasons.append(f"{prefix}: loading capability unavailable.")
            if discharge is False:
                reasons.append(f"{prefix}: discharge capability unavailable.")

            return {"loa": loa, "beam": beam, "draft": draft, "loading": loading, "discharge": discharge}

        origin = evaluate_port(origin_constraints, "Origin port")
        destination = evaluate_port(destination_constraints, "Destination port")

        delivery_window_ok = self._delivery_window_check(cargo, reasons)

        all_checks = [
            cargo_capacity_ok,
            cargo_compatibility_ok,
            origin["loa"], origin["beam"], origin["draft"],
            destination["loa"], destination["beam"], destination["draft"],
            origin["loading"], destination["discharge"],
            delivery_window_ok,
        ]

        if any(value is False for value in all_checks):
            result = "INFEASIBLE"
        elif any(value is None for value in all_checks):
            result = "REVIEW"
        else:
            result = "FEASIBLE"

        checks["origin_constraints_available"] = origin_constraints is not None
        checks["destination_constraints_available"] = destination_constraints is not None

        return {
            "result": result,
            "cargo_capacity_ok": cargo_capacity_ok,
            "cargo_compatibility_ok": cargo_compatibility_ok,
            "origin_loa_ok": origin["loa"],
            "origin_beam_ok": origin["beam"],
            "origin_draft_ok": origin["draft"],
            "destination_loa_ok": destination["loa"],
            "destination_beam_ok": destination["beam"],
            "destination_draft_ok": destination["draft"],
            "loading_capability_ok": origin["loading"],
            "discharge_capability_ok": destination["discharge"],
            "delivery_window_ok": delivery_window_ok,
            "reasons": reasons,
            "checks": checks,
            "provenance": "DERIVED",
        }
