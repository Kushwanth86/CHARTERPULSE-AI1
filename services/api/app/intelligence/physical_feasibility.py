from __future__ import annotations

from datetime import datetime, timezone


class PhysicalFeasibilityEngine:
    """Deterministic physical feasibility gate.

    The engine is intentionally conservative:
    - a known violated constraint produces ``INFEASIBLE``;
    - a required unknown produces ``REVIEW``;
    - ``FEASIBLE`` is returned only when every required check is known and passes.

    No vessel class, port, cargo or material is inferred from a hard-coded
    industry mapping. Compatibility must be supplied as source-backed data.
    """

    @staticmethod
    def _normalize(value: object) -> str:
        return " ".join(
            str(value or "")
            .strip()
            .lower()
            .replace("_", " ")
            .replace("-", " ")
            .split()
        )

    @classmethod
    def _dimension_check(
        cls,
        vessel_value,
        port_limit,
        label: str,
        reasons: list[str],
    ) -> bool | None:
        if port_limit is None:
            reasons.append(f"{label}: port limit unavailable.")
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
        vessel_cargo_capacity,
        required_quantity,
        reasons: list[str],
    ) -> bool | None:
        """Check whether the vessel can carry the requested cargo quantity."""
        if required_quantity is None or vessel_cargo_capacity is None:
            reasons.append(
                "Cargo quantity or vessel cargo capacity is unavailable."
            )
            return None

        if float(vessel_cargo_capacity) < float(required_quantity):
            reasons.append(
                "Vessel cargo capacity is insufficient for the cargo requirement."
            )
            return False

        return True

    @staticmethod
    def _dwt_check(
        vessel_dwt,
        port_max_vessel_dwt,
        reasons: list[str],
    ) -> bool | None:
        """Check vessel DWT against the applicable port maximum DWT limits."""
        if any(value is None for value in port_max_vessel_dwt):
            reasons.append(
                "A required port maximum vessel DWT limit is unavailable."
            )
            return None

        if vessel_dwt is None:
            reasons.append("Vessel DWT is unavailable.")
            return None

        effective_limit = min(
            float(value) for value in port_max_vessel_dwt
        )

        if float(vessel_dwt) > effective_limit:
            reasons.append(
                "Vessel DWT exceeds the applicable port maximum vessel DWT limit."
            )
            return False

        return True

    @classmethod
    def _explicit_vessel_cargo_compatibility(
        cls,
        cargo: dict,
        rules: list[dict] | None,
        reasons: list[str],
    ) -> bool | None:
        if not rules:
            reasons.append(
                "No source-backed vessel/cargo compatibility rule is available."
            )
            return None

        cargo_type = cls._normalize(cargo.get("cargo_type"))
        material = cls._normalize(cargo.get("material"))

        matches: list[dict] = []

        for rule in rules:
            rule_type = cls._normalize(rule.get("cargo_type"))
            rule_material = cls._normalize(rule.get("material"))

            if rule_type and cargo_type and rule_type == cargo_type:
                matches.append(rule)
            elif rule_material and material and rule_material == material:
                matches.append(rule)

        if not matches:
            reasons.append(
                "No matching source-backed vessel/cargo compatibility rule is available."
            )
            return None

        if any(rule.get("allowed") is False for rule in matches):
            reasons.append(
                "Vessel/cargo compatibility is explicitly disallowed by source-backed data."
            )
            return False

        return True

    @classmethod
    def _port_handling_check(
        cls,
        cargo: dict,
        constraints: dict | None,
        prefix: str,
        reasons: list[str],
    ) -> bool | None:
        if constraints is None:
            reasons.append(
                f"{prefix}: physical port constraints unavailable."
            )
            return None

        handling_types = constraints.get("cargo_handling_types")

        if not isinstance(handling_types, list) or not handling_types:
            reasons.append(
                f"{prefix}: cargo handling compatibility data unavailable."
            )
            return None

        cargo_identifier = (
            cargo.get("cargo_type") or cargo.get("material")
        )

        if not cargo_identifier:
            reasons.append(
                f"{prefix}: cargo type/material unavailable for handling compatibility."
            )
            return None

        normalized_identifier = cls._normalize(cargo_identifier)

        supported = {
            cls._normalize(item)
            for item in handling_types
            if item
        }

        if normalized_identifier not in supported:
            reasons.append(
                f"{prefix}: cargo type is not listed as supported handling capability."
            )
            return False

        return True

    @staticmethod
    def _availability_check(
        value,
        label: str,
        reasons: list[str],
    ) -> bool | None:
        if value is None:
            reasons.append(
                f"{label}: capability availability is unknown."
            )
            return None

        if value is False:
            reasons.append(
                f"{label}: capability unavailable."
            )
            return False

        return True

    @staticmethod
    def _delivery_window_check(
        cargo: dict,
        reasons: list[str],
    ) -> bool | None:
        latest = cargo.get("latest_delivery")

        if latest is None:
            reasons.append("Delivery deadline unavailable.")
            return None

        try:
            if isinstance(latest, str):
                latest_dt = datetime.fromisoformat(
                    latest.replace("Z", "+00:00")
                )
            else:
                latest_dt = latest

            if latest_dt.tzinfo is None:
                latest_dt = latest_dt.replace(
                    tzinfo=timezone.utc
                )

            ok = latest_dt > datetime.now(timezone.utc)

        except (TypeError, ValueError):
            reasons.append(
                "Delivery deadline could not be evaluated."
            )
            return None

        if not ok:
            reasons.append(
                "Latest delivery deadline has already passed."
            )

        return ok

    def evaluate(
        self,
        cargo: dict,
        vessel: dict,
        origin_constraints: dict | None,
        destination_constraints: dict | None,
        vessel_compatibility: list[dict] | None = None,
    ) -> dict:
        reasons: list[str] = []
        checks: dict = {}

        quantity = cargo.get("quantity_mt")
        cargo_capacity = vessel.get("cargo_capacity_mt")
        vessel_dwt = vessel.get("dwt_mt")

        origin_dwt_limit = (
            (origin_constraints or {}).get(
                "max_vessel_capacity_mt"
            )
        )

        destination_dwt_limit = (
            (destination_constraints or {}).get(
                "max_vessel_capacity_mt"
            )
        )

        # Cargo quantity vs vessel cargo capacity.
        capacity_ok = self._capacity_check(
            cargo_capacity,
            quantity,
            reasons,
        )

        # Vessel DWT vs applicable port maximum vessel DWT.
        vessel_dwt_ok = self._dwt_check(
            vessel_dwt,
            [
                origin_dwt_limit,
                destination_dwt_limit,
            ],
            reasons,
        )

        checks["cargo_capacity_mt"] = cargo_capacity
        checks["required_cargo_mt"] = quantity
        checks["vessel_dwt_mt"] = vessel_dwt
        checks["origin_max_vessel_capacity_mt"] = origin_dwt_limit
        checks["destination_max_vessel_capacity_mt"] = (
            destination_dwt_limit
        )
        checks["vessel_dwt_ok"] = vessel_dwt_ok

        cargo_compatibility_ok = (
            self._explicit_vessel_cargo_compatibility(
                cargo,
                vessel_compatibility,
                reasons,
            )
        )

        checks["vessel_cargo_compatibility_rule_count"] = len(
            vessel_compatibility or []
        )

        def evaluate_port(
            constraints: dict | None,
            prefix: str,
        ) -> dict:
            loa = self._dimension_check(
                vessel.get("loa_m"),
                (constraints or {}).get("max_loa_m"),
                f"{prefix} LOA",
                reasons,
            )

            beam = self._dimension_check(
                vessel.get("beam_m"),
                (constraints or {}).get("max_beam_m"),
                f"{prefix} beam",
                reasons,
            )

            draft = self._dimension_check(
                vessel.get("max_draft_m"),
                (constraints or {}).get("max_draft_m"),
                f"{prefix} draft",
                reasons,
            )

            handling = self._port_handling_check(
                cargo,
                constraints,
                prefix,
                reasons,
            )

            loading = self._availability_check(
                (constraints or {}).get("loading_available"),
                f"{prefix} loading",
                reasons,
            )

            discharge = self._availability_check(
                (constraints or {}).get("discharge_available"),
                f"{prefix} discharge",
                reasons,
            )

            return {
                "loa": loa,
                "beam": beam,
                "draft": draft,
                "handling": handling,
                "loading": loading,
                "discharge": discharge,
            }

        origin = evaluate_port(
            origin_constraints,
            "Origin port",
        )

        destination = evaluate_port(
            destination_constraints,
            "Destination port",
        )

        delivery_window_ok = self._delivery_window_check(
            cargo,
            reasons,
        )

        all_checks = [
            capacity_ok,
            vessel_dwt_ok,
            cargo_compatibility_ok,
            origin["loa"],
            origin["beam"],
            origin["draft"],
            destination["loa"],
            destination["beam"],
            destination["draft"],
            origin["handling"],
            destination["handling"],
            origin["loading"],
            destination["discharge"],
            delivery_window_ok,
        ]

        if any(value is False for value in all_checks):
            result = "INFEASIBLE"

        elif any(value is None for value in all_checks):
            result = "REVIEW"

        else:
            result = "FEASIBLE"

        checks["origin_constraints_available"] = (
            origin_constraints is not None
        )

        checks["destination_constraints_available"] = (
            destination_constraints is not None
        )

        checks["delivery_window_scope"] = (
            "deadline status only; route transit time is not evaluated"
        )

        return {
            "result": result,
            "cargo_capacity_ok": capacity_ok,
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