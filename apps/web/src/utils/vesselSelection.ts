import type { Vessel } from "../api";

function vesselCapacityMt(vessel: Vessel): number {
  return (
    vessel.cargo_capacity_mt ??
    vessel.dwt_mt ??
    vessel.dwt ??
    0
  );
}

export function selectRecommendedVessel(
  vessels: Vessel[],
  quantityMt: number,
): Vessel | undefined {
  const suitable = vessels
    .filter((vessel) => vesselCapacityMt(vessel) >= quantityMt)
    .sort(
      (a, b) =>
        vesselCapacityMt(a) - vesselCapacityMt(b),
    );

  return (
    suitable[0] ??
    vessels.find((vessel) =>
      String(vessel.vessel_class ?? "")
        .toLowerCase()
        .includes("panamax"),
    )
  );
}
