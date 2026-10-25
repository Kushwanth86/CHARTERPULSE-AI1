
import { useEffect, useMemo, useRef, useState } from "react";
import {
  createCargo,
  listCargo,
  listCountries,
  listPorts,
  type CargoRequirement,
  type Country,
  type Port,
} from "../api";
import {
  REFERENCE_CARGO_TYPES,
  REFERENCE_MATERIALS,
} from "../data/referenceData";
import CalendarPicker from "../components/common/CalendarPicker";
import {
  isUuid,
  normalizeCargoType,
  normalizeCountryCode,
  validateProcurementInput,
  vesselClassFromCargoType,
} from "../utils/procurementValidation";

export type ProcurementContext = {
  cargo: CargoRequirement;
  originPort: Port;
  destinationPort: Port;
  originCountry: Country;
  destinationCountry: Country;
  vesselClass: string | null;
};

type Props = {
  onCreated: (value: ProcurementContext) => void;
};

type Option = {
  id: string;
  label: string;
  meta?: string;
};

const formatLocalDate = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
};

const defaultDeliveryWindow = () => {
  const start = new Date();
  const end = new Date(start);
  end.setDate(end.getDate() + 19);

  return {
    from: formatLocalDate(start),
    to: formatLocalDate(end),
  };
};

const code = (country: Country) =>
  normalizeCountryCode(country.iso2, country.country_code, country.code);

function SearchDropdown({
  label,
  value,
  options,
  placeholder,
  disabled,
  helper,
  onChange,
}: {
  label: string;
  value: string;
  options: Option[];
  placeholder: string;
  disabled?: boolean;
  helper?: string;
  onChange: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const root = useRef<HTMLDivElement>(null);

  const selected = options.find(
    (option) => option.id === value,
  );

  const filtered = useMemo(() => {
    const search = query.trim().toLowerCase();

    const results = search
      ? options.filter((option) =>
          `${option.label} ${option.meta || ""}`
            .toLowerCase()
            .includes(search),
        )
      : options;

    return results.slice(0, 80);
  }, [options, query]);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (
        root.current &&
        !root.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", close);

    return () =>
      document.removeEventListener("mousedown", close);
  }, []);

  useEffect(() => {
    if (!open) {
      setQuery("");
    }
  }, [open]);

  return (
    <div
      className="field search-dropdown"
      ref={root}
    >
      <label htmlFor={label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}>{label}</label>

      <button
        id={label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}
        type="button"
        aria-label={label}
        aria-expanded={open}
        className={`search-trigger ${open ? "open" : ""}`}
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
      >
        <span
          className={
            selected
              ? "selected-label"
              : "placeholder-label"
          }
        >
          {selected?.label || placeholder}
        </span>

        {selected?.meta && (
          <span className="selected-meta">
            {selected.meta}
          </span>
        )}

        <span className="search-chevron">⌄</span>
      </button>

      {open && (
        <div className="search-popover">
          <div className="search-popover-input">
            <span>⌕</span>
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type to search…"
            />
          </div>

          <div className="search-results">
            {filtered.map((option) => (
              <button
                type="button"
                key={option.id}
                className={`search-option ${
                  option.id === value ? "selected" : ""
                }`}
                onClick={() => {
                  onChange(option.id);
                  setOpen(false);
                }}
              >
                <span>{option.label}</span>

                {option.meta && (
                  <small>{option.meta}</small>
                )}
              </button>
            ))}

            {!filtered.length && (
              <div className="search-empty">
                No matching records.
              </div>
            )}
          </div>

          <div className="search-count">
            Showing {filtered.length} of{" "}
            {options.length.toLocaleString()} records
          </div>
        </div>
      )}

      <small>
        {helper || "Search by name or reference code."}
      </small>
    </div>
  );
}

export default function NewProcurement({
  onCreated,
}: Props) {
  const [countries, setCountries] = useState<Country[]>([]);
  const [cargoRows, setCargoRows] = useState<
    CargoRequirement[]
  >([]);
  const [originPorts, setOriginPorts] = useState<Port[]>([]);
  const [destinationPorts, setDestinationPorts] =
    useState<Port[]>([]);

  const [originCountry, setOriginCountry] = useState("");
  const [destinationCountry, setDestinationCountry] =
    useState("");

  const [originPort, setOriginPort] = useState("");
  const [destinationPort, setDestinationPort] =
    useState("");

  const [material, setMaterial] = useState("");
  const [cargoType, setCargoType] = useState("");
  const [quantity, setQuantity] = useState("");
  const [priority, setPriority] = useState("NORMAL");

  const initialWindow = useMemo(
    () => defaultDeliveryWindow(),
    [],
  );

  const [fromDate, setFromDate] = useState(
    initialWindow.from,
  );
  const [toDate, setToDate] = useState(initialWindow.to);

  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([listCountries(), listCargo()])
      .then(([countryRows, cargo]) => {
        setCountries(countryRows);
        setCargoRows(cargo);
      })
      .catch((cause: unknown) => {
        setError(
          cause instanceof Error
            ? cause.message
            : "Unable to load procurement reference data.",
        );
      });
  }, []);

  useEffect(() => {
    let cancelled = false;

    if (!originCountry) {
      setOriginPorts([]);
      setOriginPort("");
      return;
    }

    setOriginPort("");
    setOriginPorts([]);

    listPorts(originCountry)
      .then((ports) => {
        if (!cancelled) setOriginPorts(ports);
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          setError(
            cause instanceof Error
              ? cause.message
              : "Unable to load origin ports.",
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [originCountry]);

  useEffect(() => {
    let cancelled = false;

    if (!destinationCountry) {
      setDestinationPorts([]);
      setDestinationPort("");
      return;
    }

    setDestinationPort("");
    setDestinationPorts([]);

    listPorts(destinationCountry)
      .then((ports) => {
        if (!cancelled) setDestinationPorts(ports);
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          setError(
            cause instanceof Error
              ? cause.message
              : "Unable to load destination ports.",
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [destinationCountry]);

  const countriesOptions = useMemo(
    () =>
      countries
        .filter((country) => code(country))
        .map((country) => ({
          id: code(country),
          label: country.name,
          meta: `${code(country)}${
            country.iso3 ? ` / ${country.iso3}` : ""
          }`,
        })),
    [countries],
  );

  const materialOptions = useMemo(() => {
    const values = [
      ...REFERENCE_MATERIALS,
      ...cargoRows.map((row) => row.material ?? ""),
    ]
      .map((value) => value.trim())
      .filter(Boolean);
    const uniqueValues = new Map<string, string>();

    for (const value of values) {
      const key = value.toLocaleLowerCase();
      if (!uniqueValues.has(key)) uniqueValues.set(key, value);
    }

    return [...uniqueValues.values()].map((value) => ({
      id: value,
      label: value,
      meta: "Bulk commodity",
    }));
  }, [cargoRows]);

  const cargoOptions = useMemo(() => {
    const databaseTypes = cargoRows
      .map((row) => row.cargo_type?.trim() ?? "")
      .filter(Boolean);
    const rawTypes = [
      ...REFERENCE_CARGO_TYPES.map((item) => item.id),
      ...databaseTypes,
    ];
    const uniqueTypes = new Map<string, string>();

    for (const rawType of rawTypes) {
      const canonicalReference = REFERENCE_CARGO_TYPES.find(
        (item) => item.id.toUpperCase() === rawType.toUpperCase(),
      )?.id;
      const id = canonicalReference ?? rawType;
      const key = id.toUpperCase();
      if (!uniqueTypes.has(key)) uniqueTypes.set(key, id);
    }

    return [...uniqueTypes.values()].map((id) => {
      const reference = REFERENCE_CARGO_TYPES.find(
        (item) => item.id === id,
      );

      return {
        id,
        label: reference?.label || id.replace(/_/g, " "),
        meta: reference?.meta || id,
      };
    });
  }, [cargoRows]);

  const originOptions = useMemo(
    () =>
      originPorts
        .filter(
          (port) =>
            isUuid(port.location_id) &&
            String(port.unlocode ?? "").toUpperCase().startsWith(originCountry),
        )
        .map((port) => ({
          id: port.id,
          label: port.name,
          meta: port.unlocode || "UN/LOCODE unavailable",
        })),
    [originPorts, originCountry],
  );

  const destinationOptions = useMemo(
    () =>
      destinationPorts
        .filter(
          (port) =>
            isUuid(port.location_id) &&
            String(port.unlocode ?? "").toUpperCase().startsWith(destinationCountry),
        )
        .map((port) => ({
          id: port.id,
          label: port.name,
          meta: port.unlocode || "UN/LOCODE unavailable",
        })),
    [destinationPorts, destinationCountry],
  );

  const op = originPorts.find(
    (port) => port.id === originPort,
  );

  const dp = destinationPorts.find(
    (port) => port.id === destinationPort,
  );

  const oc = countries.find(
    (country) => code(country) === originCountry,
  );

  const dc = countries.find(
    (country) => code(country) === destinationCountry,
  );

  async function submit() {
    if (saving) return;

    setError("");

    const validationError = validateProcurementInput({
      material,
      cargoType,
      originCountry,
      destinationCountry,
      originPortLocationId: op?.location_id,
      destinationPortLocationId: dp?.location_id,
      originPortUnlocode: op?.unlocode,
      destinationPortUnlocode: dp?.unlocode,
      quantity,
      fromDate,
      toDate,
      today: formatLocalDate(new Date()),
      priority,
    });

    if (validationError) {
      setError(validationError);
      return;
    }

    // The validator has confirmed these selected records are present.
    if (!op || !dp || !oc || !dc) {
      setError("Select valid countries and ports before submitting.");
      return;
    }

    const parsedQuantity = Number(quantity);
    setSaving(true);

    try {
      const cargo = await createCargo({
        cargo_type: normalizeCargoType(cargoType),
        material: material.trim(),
        quantity_mt: parsedQuantity,
        origin_location_id: op.location_id,
        destination_location_id: dp.location_id,
        earliest_delivery: `${fromDate}T00:00:00`,
        latest_delivery: `${toDate}T23:59:59`,
        priority,
      });

      onCreated({
        cargo,
        originPort: op,
        destinationPort: dp,
        originCountry: oc,
        destinationCountry: dc,
        vesselClass: vesselClassFromCargoType(cargoType),
      });
    } catch (cause: unknown) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Unable to create procurement.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <span className="eyebrow">
            OPERATIONS / PROCUREMENT
          </span>
          <h1>New Procurement</h1>
          <p>
            Define the cargo, trade lane and delivery
            window. Reference selectors are populated
            from available reference and API data.
          </p>
        </div>

        <span className="data-badge proxy">
          REFERENCE + API
        </span>
      </div>

      <section className="enterprise-card procurement-card">
        <div className="section-head">
          <div>
            <span className="eyebrow">
              01 · CARGO REQUIREMENT
            </span>
            <h2>Procurement intake</h2>
          </div>
          <span className="step-chip">
            MANDATORY INPUTS
          </span>
        </div>

        <div className="form-grid three">
          <div className="field">
            <label htmlFor="procurement-material">MATERIAL</label>
            <input
              id="procurement-material"
              type="text"
              list="procurement-material-options"
              value={material}
              onChange={(event) => {
                setMaterial(event.target.value);
                setError("");
              }}
              placeholder="Enter a commodity or choose a suggestion"
              autoComplete="off"
            />
            <datalist id="procurement-material-options">
              {materialOptions.map((option) => (
                <option key={option.id} value={option.id} />
              ))}
            </datalist>
            <small>
              Enter any commodity. Suggestions include reference examples and prior procurements.
            </small>
          </div>

          <SearchDropdown
            label="CARGO TYPE"
            value={cargoType}
            options={cargoOptions}
            placeholder="Select standardized cargo type"
            helper="Dry-bulk transport classification."
            onChange={(value) => {
              setCargoType(value);
              setError("");
            }}
          />

          <div className="field">
            <label>QUANTITY</label>
            <div className="input-unit">
              <input
                type="number"
                step="any"
                value={quantity}
                onChange={(event) => {
                  setQuantity(event.target.value);
                  setError("");
                }}
                aria-label="Quantity in metric tonnes"
              />
              <span>MT</span>
            </div>
            <small>Metric tonnes required.</small>
          </div>
        </div>

        <div className="form-divider">
          <span>TRADE LANE</span>
        </div>

        <div className="form-grid two">
          <SearchDropdown
            label="ORIGIN COUNTRY"
            value={originCountry}
            options={countriesOptions}
            placeholder="Search country / ISO2 / ISO3"
            onChange={(value) => {
              setOriginCountry(value);
              setError("");
            }}
          />

          <SearchDropdown
            label="ORIGIN PORT"
            value={originPort}
            options={originOptions}
            placeholder={
              originCountry
                ? "Search ports in selected country"
                : "Select origin country first"
            }
            helper={
              originOptions.length
                ? `${originOptions.length.toLocaleString()} valid ports available.`
                : "No valid live ports loaded. Reference-only ports cannot be saved; check API connectivity."
            }
            disabled={!originCountry || originOptions.length === 0}
            onChange={(value) => {
              setOriginPort(value);
              setError("");
            }}
          />
        </div>

        <div className="form-grid two">
          <SearchDropdown
            label="DESTINATION COUNTRY"
            value={destinationCountry}
            options={countriesOptions}
            placeholder="Search country / ISO2 / ISO3"
            onChange={(value) => {
              setDestinationCountry(value);
              setError("");
            }}
          />

          <SearchDropdown
            label="DESTINATION PORT"
            value={destinationPort}
            options={destinationOptions}
            placeholder={
              destinationCountry
                ? "Search ports in selected country"
                : "Select destination country first"
            }
            helper={
              destinationOptions.length
                ? `${destinationOptions.length.toLocaleString()} valid ports available.`
                : "No valid live ports loaded. Reference-only ports cannot be saved; check API connectivity."
            }
            disabled={!destinationCountry || destinationOptions.length === 0}
            onChange={(value) => {
              setDestinationPort(value);
              setError("");
            }}
          />
        </div>

        <div className="calendar-window">
          <div className="section-head compact">
            <div>
              <span className="eyebrow">
                02 · DELIVERY WINDOW
              </span>
              <h3>Exact laycan / delivery dates</h3>
            </div>
            <span className="field-note">
              Popup calendar · inclusive dates
            </span>
          </div>

          <div className="form-grid two">
            <CalendarPicker
              label="FROM DATE"
              value={fromDate}
              onChange={(value) => {
                setFromDate(value);
                setError("");
              }}
            />

            <CalendarPicker
              label="TO DATE"
              value={toDate}
              min={fromDate}
              onChange={(value) => {
                setToDate(value);
                setError("");
              }}
            />
          </div>

          <div className="date-range-readout">
            <span>SELECTED WINDOW</span>
            <strong>
              {new Date(
                `${fromDate}T12:00:00`,
              ).toLocaleDateString("en-GB", {
                weekday: "short",
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}{" "}
              →{" "}
              {new Date(
                `${toDate}T12:00:00`,
              ).toLocaleDateString("en-GB", {
                weekday: "short",
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
            </strong>
          </div>
        </div>

        <div className="form-grid two">
          <div className="field">
            <label htmlFor="procurement-priority">PRIORITY</label>
            <select
              id="procurement-priority"
              value={priority}
              onChange={(e) => {
                setPriority(e.target.value);
                setError("");
              }}
            >
              <option value="LOW">Low</option>
              <option value="NORMAL">Normal</option>
              <option value="HIGH">High</option>
              <option value="CRITICAL">Critical</option>
            </select>
            <small>
              Used as procurement urgency metadata.
            </small>
          </div>

          <div className="procurement-preview">
            <span>LIVE REQUIREMENT PREVIEW</span>
            <strong>
              {material} ·{" "}
              {(
                quantity.trim() &&
                Number.isFinite(Number(quantity))
                  ? Number(quantity)
                  : 0
              ).toLocaleString()}{" "}
              MT
            </strong>
            <div>
              {op?.name || "Origin port"} →{" "}
              {dp?.name || "Destination port"}
            </div>
            <small>
              {fromDate} → {toDate} · {priority}
            </small>
          </div>
        </div>

        {error && (
          <div className="error-banner" role="alert">
            {error}
          </div>
        )}

        <div className="submit-row">
          <div>
            <strong>
              Ready for decision intelligence
            </strong>
            <span>
              Create a requirement using valid location
              identifiers to continue to the decision room.
            </span>
          </div>

          <button
            className="primary-button"
            onClick={submit}
            disabled={saving}
          >
            {saving
              ? "CREATING REQUIREMENT…"
              : "CREATE PROCUREMENT & OPEN DECISION ROOM"}
          </button>
        </div>
      </section>
    </div>
  );
}
