const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const PRIORITIES = new Set(["LOW", "NORMAL", "HIGH", "CRITICAL"]);

export function isUuid(value: string | null | undefined): boolean {
  return typeof value === "string" && UUID_PATTERN.test(value);
}

export function normalizeCountryCode(...values: unknown[]): string {
  for (const value of values) {
    const candidate = String(value ?? "").trim().toUpperCase();
    if (/^[A-Z]{2}$/.test(candidate)) return candidate;
  }
  return "";
}

export function isValidUnlocode(value: string | null | undefined): boolean {
  const candidate = String(value ?? "").trim().toUpperCase();
  return /^[A-Z]{2}[A-Z0-9]{3}$/.test(candidate);
}

export function vesselClassFromCargoType(value: string): string | null {
  const normalized = value.trim().toUpperCase();
  const match = normalized.match(/^DRY_BULK_(PANAMAX|CAPESIZE|HANDYSIZE)$/);
  return match
    ? match[1].charAt(0) + match[1].slice(1).toLowerCase()
    : null;
}

export function normalizeCargoType(value: string): string {
  const normalized = value.trim();
  return /^DRY_BULK(?:_|$)/i.test(normalized)
    ? "DRY_BULK"
    : normalized;
}

function isValidIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;

  // Python datetime (the API parser) does not support year zero.
  if (Number(value.slice(0, 4)) < 1) return false;

  const parsed = new Date(value + "T00:00:00.000Z");
  return (
    Number.isFinite(parsed.getTime()) &&
    parsed.toISOString().slice(0, 10) === value
  );
}

export type ProcurementValidationInput = {
  material: string;
  cargoType: string;
  originCountry: string;
  destinationCountry: string;
  originPortLocationId?: string | null;
  destinationPortLocationId?: string | null;
  originPortUnlocode?: string | null;
  destinationPortUnlocode?: string | null;
  quantity: string;
  fromDate: string;
  toDate: string;
  today: string;
  priority: string;
};

export function validateProcurementInput(
  input: ProcurementValidationInput,
): string | null {
  const material = input.material.trim();

  if (!material) return "Enter a material or commodity.";
  if (!input.cargoType.trim()) return "Select a cargo type.";
  if (!input.originCountry.trim() || !input.destinationCountry.trim()) {
    return "Select both origin and destination countries.";
  }

  if (
    !String(input.originPortLocationId ?? "").trim() ||
    !String(input.destinationPortLocationId ?? "").trim()
  ) {
    return "Select both origin and destination ports.";
  }

  if (
    !isUuid(input.originPortLocationId) ||
    !isUuid(input.destinationPortLocationId)
  ) {
    return "The selected ports do not have valid live location IDs. Select ports backed by verified API location data.";
  }

  const originUnlocode = String(input.originPortUnlocode ?? "").trim().toUpperCase();
  const destinationUnlocode = String(input.destinationPortUnlocode ?? "").trim().toUpperCase();
  const originCountry = input.originCountry.trim().toUpperCase();
  const destinationCountry = input.destinationCountry.trim().toUpperCase();

  if (!/^[A-Z]{2}[A-Z0-9]{3}$/.test(originUnlocode)) {
    return "The origin port is missing a valid UN/LOCODE.";
  }
  if (!/^[A-Z]{2}[A-Z0-9]{3}$/.test(destinationUnlocode)) {
    return "The destination port is missing a valid UN/LOCODE.";
  }
  if (originUnlocode.slice(0, 2) !== originCountry) {
    return "The origin port does not belong to the selected origin country. Reselect the port.";
  }
  if (destinationUnlocode.slice(0, 2) !== destinationCountry) {
    return "The destination port does not belong to the selected destination country. Reselect the port.";
  }
  if (
    input.originPortLocationId === input.destinationPortLocationId ||
    originUnlocode === destinationUnlocode
  ) {
    return "Origin and destination must be different locations.";
  }

  if (!input.quantity.trim()) {
    return "Enter a cargo quantity in metric tonnes.";
  }
  const quantityText = input.quantity.trim();
  // Match decimal/scientific numeric syntax; Number() alone also accepts hex, binary and octal.
  if (!/^(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][+-]?\\d+)?$/.test(quantityText)) {
    return "Quantity must be a positive finite number of metric tonnes.";
  }
  const quantity = Number(quantityText);
  if (!Number.isFinite(quantity) || quantity <= 0) {
    return "Quantity must be a positive finite number of metric tonnes.";
  }

  if (!isValidIsoDate(input.fromDate) || !isValidIsoDate(input.toDate)) {
    return "Enter valid start and end dates.";
  }
  if (!isValidIsoDate(input.today)) {
    return "Unable to validate the delivery window against today's date. Refresh and try again.";
  }
  if (input.fromDate < input.today) {
    return "From Date cannot be in the past.";
  }
  if (input.fromDate > input.toDate) {
    return "From Date must be on or before To Date.";
  }

  if (!PRIORITIES.has(input.priority)) {
    return "Select a valid procurement priority.";
  }

  return null;
}
