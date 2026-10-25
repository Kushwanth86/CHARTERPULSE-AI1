import test from "node:test";
import assert from "node:assert/strict";
import type { Vessel } from "../src/api";
import {
  selectRecommendedVessel,
  vesselCapacityMt,
} from "../src/utils/vesselSelection";

function vessel(
  overrides: Partial<Vessel> & Pick<Vessel, "id" | "name" | "provenance">,
): Vessel {
  return {
    vessel_class: "Bulk Carrier",
    cargo_capacity_mt: null,
    dwt: null,
    dwt_mt: null,
    ...overrides,
  };
}

test("recommendation uses dwt_mt when cargo capacity is not populated", () => {
  const smaller = vessel({
    id: "small",
    name: "SMALL BULKER",
    provenance: "PUBLIC_PROXY",
    dwt_mt: 60000,
  });
  const suitable = vessel({
    id: "suitable",
    name: "OCEAN EMERALD",
    provenance: "PUBLIC_PROXY",
    dwt_mt: 92950,
  });

  assert.equal(
    selectRecommendedVessel([smaller, suitable], 70000),
    suitable,
  );
  assert.equal(vesselCapacityMt(suitable), 92950);
});

test("recommendation chooses the smallest suitable vessel by available capacity", () => {
  const larger = vessel({
    id: "larger",
    name: "LARGE BULKER",
    provenance: "PUBLIC_PROXY",
    dwt_mt: 120000,
  });
  const smallerSuitable = vessel({
    id: "smaller-suitable",
    name: "MEDIUM BULKER",
    provenance: "PUBLIC_PROXY",
    dwt_mt: 80000,
  });

  assert.equal(
    selectRecommendedVessel([larger, smallerSuitable], 70000),
    smallerSuitable,
  );
});

test("populated cargo capacity takes precedence over deadweight", () => {
  const vesselWithKnownCapacity = vessel({
    id: "capacity-known",
    name: "CAPACITY-KNOWN BULKER",
    provenance: "PUBLIC_PROXY",
    cargo_capacity_mt: 65000,
    dwt_mt: 100000,
  });

  assert.equal(vesselCapacityMt(vesselWithKnownCapacity), 65000);
  assert.notEqual(
    selectRecommendedVessel([vesselWithKnownCapacity], 70000),
    vesselWithKnownCapacity,
  );
});
