from typing import Any

from services.api.app.repositories.supabase_client import get_supabase_client


class PortIntelligenceService:
    """Read-only global port intelligence queries for the API."""

    def __init__(self):
        self.client = get_supabase_client()

    def summary(self) -> dict[str, int]:
        """Return authoritative counts from the live Supabase tables."""
        countries = (
            self.client.table("countries")
            .select("id", count="exact")
            .execute()
        )
        regions = (
            self.client.table("regions")
            .select("id", count="exact")
            .execute()
        )
        locations = (
            self.client.table("locations")
            .select("id", count="exact")
            .execute()
        )
        ports = (
            self.client.table("ports")
            .select("id", count="exact")
            .execute()
        )

        return {
            "countries": countries.count or 0,
            "regions": regions.count or 0,
            "locations": locations.count or 0,
            "ports": ports.count or 0,
        }

    def search_ports(
        self,
        query: str | None = None,
        country_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Search ports with database-side pagination and optional country filter."""
        select_clause = (
            "id,location_id,name,latitude,longitude,"
            "max_draft_m,max_loa_m,max_beam_m,"
            "annual_capacity_tonnes,storage_capacity_tonnes,"
            "rail_connected,road_connected,pipeline_connected,"
            "unlocode,source,source_url,observed_at,updated_at"
        )

        if country_id:
            select_clause += ",locations!inner(country_id)"

        query_builder = (
            self.client.table("ports")
            .select(select_clause)
            .order("name")
            .range(offset, offset + limit - 1)
        )

        if query:
            query_builder = query_builder.ilike("name", f"%{query}%")

        if country_id:
            query_builder = query_builder.eq("locations.country_id", country_id)

        response = query_builder.execute()
        ports = response.data or []

        if not ports:
            return []

        location_ids = list({item["location_id"] for item in ports})

        locations_response = (
            self.client.table("locations")
            .select("id,country_id,region_id,name,latitude,longitude,timezone")
            .in_("id", location_ids)
            .execute()
        )
        locations = {
            item["id"]: item for item in (locations_response.data or [])
        }

        country_ids = list({
            item["country_id"]
            for item in locations.values()
            if item.get("country_id")
        })

        countries_response = (
            self.client.table("countries")
            .select("id,iso2,iso3,name")
            .in_("id", country_ids)
            .execute()
            if country_ids
            else None
        )
        countries = {
            item["id"]: item
            for item in (countries_response.data or [])
        } if countries_response else {}

        enriched = []

        for port in ports:
            port = dict(port)
            port.pop("locations", None)

            location = locations.get(port["location_id"], {})
            country = countries.get(location.get("country_id"), {})

            enriched.append({
                **port,
                "location": location,
                "country": country,
            })

        return enriched
