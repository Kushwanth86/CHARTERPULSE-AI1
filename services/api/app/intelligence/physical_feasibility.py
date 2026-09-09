from __future__ import annotations

from datetime import datetime, timezone


class PhysicalFeasibilityEngine:
    """
    Physical feasibility gate.

    IMPORTANT:
    Missing physical data does not become "true".

    A missing constraint produces REVIEW where appropriate.
    A known violated constraint produces INFEASIBLE.
    """

    def _dimension_check(
        self,
        vessel_value,
        port_limit,
        label: str,
        reasons: list,
    ) -> bool | None:

        if port_limit is None:
            return None

        if vessel_value is None:
            reasons.append(
                f"{label}: vessel dimension unavailable."
            )
            return None

        if vessel_value > port_limit:
            reasons.append(
                f"{label}: vessel exceeds port limit."
            )
            return False

        return True

    def evaluate(
        self,
        cargo: dict,
        vessel: dict,
        origin_constraints: dict | None,
        destination_constraints: dict | None,
    ) -> dict:

        reasons = []
        checks = {}

        quantity = cargo.get("quantity_mt")
        capacity = vessel.get("cargo_capacity_mt")

        # ------------------------------------------------------
        # Cargo capacity
        # ------------------------------------------------------

        if quantity is None or capacity is None:
            cargo_capacity_ok = None

            reasons.append(
                "Cargo quantity or vessel cargo capacity is unavailable."
            )

        else:
            cargo_capacity_ok = float(capacity) >= float(quantity)

            if not cargo_capacity_ok:
                reasons.append(
                    "Vessel cargo capacity is insufficient."
                )

        checks["cargo_capacity_mt"] = capacity
        checks["required_cargo_mt"] = quantity

        # ------------------------------------------------------
        # Cargo compatibility
        # ------------------------------------------------------

        cargo_type = (
            cargo.get("cargo_type")
            or cargo.get("material")
            or ""
        ).strip().lower()

        ship_type = (
            vessel.get("ship_type")
            or ""
        ).strip().lower()

        compatibility = True

        if cargo_type and ship_type:
            dry_bulk_terms = {
                "coal",
                "iron ore",
                "ore",
                "grain",
                "steel",
                "bulk",
            }

            tanker_terms = {
                "oil",
                "crude",
                "petroleum",
                "chemical",
                "liquid",
            }

            if (
                any(term in cargo_type for term in tanker_terms)
                and "tanker" not in ship_type
            ):
                compatibility = False

            if (
                any(term in cargo_type for term in dry_bulk_terms)
                and "tanker" in ship_type
            ):
                compatibility = False

        else:
            compatibility = None

        cargo_compatibility_ok = compatibility

        if compatibility is False:
            reasons.append(
                "Cargo and vessel type are incompatible."
            )
        elif compatibility is None:
            reasons.append(
                "Cargo/vessel compatibility requires additional data."
            )

        checks["cargo_type"] = cargo_type or None
        checks["ship_type"] = ship_type or None

        # ------------------------------------------------------
        # Port constraints
        # ------------------------------------------------------

        def evaluate_port(
            constraints: dict | None,
            prefix: str,
        ) -> dict:

            if not constraints:
                reasons.append(
                    f"{prefix}: physical port constraints unavailable."
                )

                return {
                    "loa": None,
                    "beam": None,
                    "draft": None,
                    "loading": None,
                    "discharge": None,
                }

            loa = self._dimension_check(
                vessel.get("loa_m"),
                constraints.get("max_loa_m"),
                f"{prefix} LOA",
                reasons,
            )

            beam = self._dimension_check(
                vessel.get("beam_m"),
                constraints.get("max_beam_m"),
                f"{prefix} beam",
                reasons,
            )

            draft = self._dimension_check(
                vessel.get("max_draft_m"),
                constraints.get("max_draft_m"),
                f"{prefix} draft",
                reasons,
            )

            loading = constraints.get("loading_available")
            discharge = constraints.get("discharge_available")

            if loading is False:
                reasons.append(
                    f"{prefix}: loading capability unavailable."
                )

            if discharge is False:
                reasons.append(
                    f"{prefix}: discharge capability unavailable."
                )

            return {
                "loa": loa,
                "beam": beam,
                "draft": draft,
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

        origin_loa_ok = origin["loa"]
        origin_beam_ok = origin["beam"]
        origin_draft_ok = origin["draft"]

        destination_loa_ok = destination["loa"]
        destination_beam_ok = destination["beam"]
        destination_draft_ok = destination["draft"]

        loading_capability_ok = origin["loading"]
        discharge_capability_ok = destination["discharge"]

        # ------------------------------------------------------
        # Delivery window
        # ------------------------------------------------------

        now = datetime.now(timezone.utc)

        earliest = cargo.get("earliest_delivery")
        latest = cargo.get("latest_delivery")

        if latest is None:
            delivery_window_ok = None
            reasons.append(
                "Delivery deadline unavailable."
            )
        else:
            try:
                if isinstance(latest, str):
                    latest_dt = datetime.fromisoformat(
                        latest.replace("Z", "+00:00")
                    )
                else:
                    latest_dt = latest

                delivery_window_ok = latest_dt > now

            except (TypeError, ValueError):
                delivery_window_ok = None

                reasons.append(
                    "Delivery deadline could not be evaluated."
                )

        checks["earliest_delivery"] = earliest
        checks["latest_delivery"] = latest

        # ------------------------------------------------------
        # Result classification
        # ------------------------------------------------------

        all_checks = [
            cargo_capacity_ok,
            cargo_compatibility_ok,

            origin_loa_ok,
            origin_beam_ok,
            origin_draft_ok,

            destination_loa_ok,
            destination_beam_ok,
            destination_draft_ok,

            loading_capability_ok,
            discharge_capability_ok,

            delivery_window_ok,
        ]

        if any(value is False for value in all_checks):
            result = "INFEASIBLE"

        elif any(value is None for value in all_checks):
            result = "REVIEW"

        else:
            result = "FEASIBLE"

        return {
            "result": result,

            "cargo_capacity_ok": cargo_capacity_ok,
            "cargo_compatibility_ok": cargo_compatibility_ok,

            "origin_loa_ok": origin_loa_ok,
            "origin_beam_ok": origin_beam_ok,
            "origin_draft_ok": origin_draft_ok,

            "destination_loa_ok": destination_loa_ok,
            "destination_beam_ok": destination_beam_ok,
            "destination_draft_ok": destination_draft_ok,

            "loading_capability_ok": loading_capability_ok,
            "discharge_capability_ok": discharge_capability_ok,

            "delivery_window_ok": delivery_window_ok,

            "reasons": reasons,
            "checks": checks,

            "provenance": "DERIVED",
        }
