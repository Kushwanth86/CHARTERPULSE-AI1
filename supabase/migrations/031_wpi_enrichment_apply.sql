-- CHARTERPULSE AI
-- Migration 031: Controlled NGA WPI enrichment apply path
--
-- WPI values are source-backed operational observations. The existing
-- port_constraints provenance is row-level, so field-level WPI lineage is
-- retained separately in operational_provenance instead of relabeling a
-- mixed-source constraint row as wholly REAL.

ALTER TABLE public.ports
    ADD COLUMN IF NOT EXISTS operational_provenance jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE public.port_constraints
    ADD COLUMN IF NOT EXISTS operational_provenance jsonb NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN public.ports.operational_provenance IS
    'Field-level operational provenance for values such as rail connectivity. Does not replace the port identity source fields.';

COMMENT ON COLUMN public.port_constraints.operational_provenance IS
    'Field-level operational provenance for WPI-enriched constraint values. Row-level provenance remains the provenance of the existing constraint record.';

CREATE OR REPLACE FUNCTION public.apply_wpi_enrichment(p_plan jsonb)
RETURNS jsonb
LANGUAGE plpgsql
VOLATILE
SET search_path = public
AS $$
DECLARE
    plan_item jsonb;
    action_item jsonb;
    port_id_value uuid;
    field_name text;
    action_name text;
    current_value text;
    wpi_value jsonb;
    expected_current jsonb;
    port_exists boolean;
    constraint_id uuid;
    constraint_provenance text;
    current_cargo jsonb;
    wpi_cargo text[];
    metadata jsonb;
    counts jsonb := jsonb_build_object(
        'ports_touched', 0,
        'constraints_created', 0,
        'field_actions', 0,
        'fill_null', 0,
        'replace_simulated', 0
    );
BEGIN
    IF jsonb_typeof(p_plan) <> 'array' THEN
        RAISE EXCEPTION 'WPI enrichment plan must be a JSON array';
    END IF;

    FOR plan_item IN
        SELECT value
        FROM jsonb_array_elements(p_plan)
    LOOP
        IF plan_item->>'port_id' IS NULL THEN
            RAISE EXCEPTION 'WPI enrichment plan item is missing port_id';
        END IF;

        port_id_value := (plan_item->>'port_id')::uuid;

        SELECT EXISTS (
            SELECT 1 FROM public.ports WHERE id = port_id_value
        ) INTO port_exists;

        IF NOT port_exists THEN
            RAISE EXCEPTION 'WPI enrichment port does not exist: %', port_id_value;
        END IF;

        FOR action_item IN
            SELECT value
            FROM jsonb_array_elements(COALESCE(plan_item->'actions', '[]'::jsonb))
        LOOP
            field_name := action_item->>'field';
            action_name := action_item->>'action';
            wpi_value := action_item->'wpi';
            expected_current := action_item->'current';

            IF action_name NOT IN ('FILL_NULL', 'REPLACE_SIMULATED') THEN
                RAISE EXCEPTION 'Unsupported WPI enrichment action: %', action_name;
            END IF;

            IF wpi_value IS NULL OR wpi_value = 'null'::jsonb THEN
                RAISE EXCEPTION 'WPI enrichment action has null WPI value: %', field_name;
            END IF;

            metadata := jsonb_build_object(
                'source', 'NGA World Port Index',
                'source_url', 'https://fgmod.nga.mil/nauticalpubs-feature/rest/services/WPI/WPI_Viewer/FeatureServer/0',
                'provenance', 'REAL',
                'applied_at', now()
            );

            IF field_name = 'rail_connected' THEN
                IF action_name <> 'FILL_NULL' THEN
                    RAISE EXCEPTION 'rail_connected only supports FILL_NULL';
                END IF;

                IF NOT EXISTS (
                    SELECT 1
                    FROM public.ports
                    WHERE id = port_id_value
                      AND rail_connected IS NULL
                ) THEN
                    RAISE EXCEPTION 'Stale WPI plan for rail_connected on port %', port_id_value;
                END IF;

                UPDATE public.ports
                SET rail_connected = (wpi_value #>> '{}')::boolean,
                    operational_provenance = operational_provenance || jsonb_build_object(field_name, metadata),
                    updated_at = now()
                WHERE id = port_id_value;

                counts := jsonb_set(
                    counts,
                    '{fill_null}',
                    to_jsonb((counts->>'fill_null')::integer + 1)
                );

            ELSIF field_name IN ('max_loa_m', 'max_beam_m', 'max_draft_m') THEN
                SELECT id, provenance
                INTO constraint_id, constraint_provenance
                FROM public.port_constraints
                WHERE port_id = port_id_value;

                IF action_name = 'FILL_NULL' THEN
                    IF constraint_id IS NULL THEN
                        INSERT INTO public.port_constraints (
                            port_id,
                            max_loa_m,
                            max_beam_m,
                            max_draft_m,
                            source,
                            source_reference,
                            provenance,
                            observed_at,
                            operational_provenance
                        )
                        VALUES (
                            port_id_value,
                            CASE WHEN field_name = 'max_loa_m' THEN (wpi_value #>> '{}')::numeric ELSE NULL END,
                            CASE WHEN field_name = 'max_beam_m' THEN (wpi_value #>> '{}')::numeric ELSE NULL END,
                            CASE WHEN field_name = 'max_draft_m' THEN (wpi_value #>> '{}')::numeric ELSE NULL END,
                            'NGA World Port Index',
                            'https://fgmod.nga.mil/nauticalpubs-feature/rest/services/WPI/WPI_Viewer/FeatureServer/0',
                            'REAL',
                            NULL,
                            jsonb_build_object(field_name, metadata)
                        )
                        RETURNING id INTO constraint_id;

                        counts := jsonb_set(
                            counts,
                            '{constraints_created}',
                            to_jsonb((counts->>'constraints_created')::integer + 1)
                        );
                    ELSE
                        IF EXISTS (
                            SELECT 1
                            FROM public.port_constraints pc
                            WHERE pc.id = constraint_id
                              AND (
                                  (field_name = 'max_loa_m' AND pc.max_loa_m IS NOT NULL)
                                  OR (field_name = 'max_beam_m' AND pc.max_beam_m IS NOT NULL)
                                  OR (field_name = 'max_draft_m' AND pc.max_draft_m IS NOT NULL)
                              )
                        ) THEN
                            RAISE EXCEPTION 'Stale WPI plan: % is no longer NULL on port %', field_name, port_id_value;
                        END IF;

                        EXECUTE format(
                            'UPDATE public.port_constraints SET %I = $1, operational_provenance = operational_provenance || $2, updated_at = now() WHERE id = $3',
                            field_name
                        ) USING (wpi_value #>> '{}')::numeric,
                                jsonb_build_object(field_name, metadata),
                                constraint_id;
                    END IF;

                    counts := jsonb_set(
                        counts,
                        '{fill_null}',
                        to_jsonb((counts->>'fill_null')::integer + 1)
                    );

                ELSE
                    IF constraint_id IS NULL THEN
                        RAISE EXCEPTION 'REPLACE_SIMULATED requires an existing constraint for port %', port_id_value;
                    END IF;

                    IF constraint_provenance <> 'SIMULATED' THEN
                        RAISE EXCEPTION 'REPLACE_SIMULATED requires SIMULATED provenance for port %', port_id_value;
                    END IF;

                    IF field_name = 'max_loa_m' THEN
                        SELECT max_loa_m::text INTO current_value FROM public.port_constraints WHERE id = constraint_id;
                    ELSIF field_name = 'max_beam_m' THEN
                        SELECT max_beam_m::text INTO current_value FROM public.port_constraints WHERE id = constraint_id;
                    ELSE
                        SELECT max_draft_m::text INTO current_value FROM public.port_constraints WHERE id = constraint_id;
                    END IF;

                    IF current_value IS DISTINCT FROM action_item->>'current' THEN
                        RAISE EXCEPTION 'Stale WPI plan for simulated % on port %: expected %, found %',
                            field_name, port_id_value, action_item->>'current', current_value;
                    END IF;

                    EXECUTE format(
                        'UPDATE public.port_constraints SET %I = $1, operational_provenance = operational_provenance || $2, updated_at = now() WHERE id = $3',
                        field_name
                    ) USING (wpi_value #>> '{}')::numeric,
                            jsonb_build_object(field_name, metadata),
                            constraint_id;

                    counts := jsonb_set(
                        counts,
                        '{replace_simulated}',
                        to_jsonb((counts->>'replace_simulated')::integer + 1)
                    );
                END IF;

            ELSIF field_name = 'cargo_handling_types' THEN
                SELECT id, provenance, CASE
                    WHEN cargo_handling_types IS NULL THEN 'null'::jsonb
                    ELSE to_jsonb(cargo_handling_types)
                END
                INTO constraint_id, constraint_provenance, current_cargo
                FROM public.port_constraints
                WHERE port_id = port_id_value;

                wpi_cargo := ARRAY(
                    SELECT jsonb_array_elements_text(wpi_value)
                );

                IF action_name <> 'FILL_NULL' THEN
                    RAISE EXCEPTION 'cargo_handling_types does not support REPLACE_SIMULATED';
                END IF;

                IF constraint_id IS NULL THEN
                    INSERT INTO public.port_constraints (
                        port_id,
                        cargo_handling_types,
                        source,
                        source_reference,
                        provenance,
                        observed_at,
                        operational_provenance
                    )
                    VALUES (
                        port_id_value,
                        wpi_cargo,
                        'NGA World Port Index',
                        'https://fgmod.nga.mil/nauticalpubs-feature/rest/services/WPI/WPI_Viewer/FeatureServer/0',
                        'REAL',
                        NULL,
                        jsonb_build_object(field_name, metadata)
                    )
                    RETURNING id INTO constraint_id;

                    counts := jsonb_set(
                        counts,
                        '{constraints_created}',
                        to_jsonb((counts->>'constraints_created')::integer + 1)
                    );
                ELSE
                    IF current_cargo <> 'null'::jsonb THEN
                        RAISE EXCEPTION 'Stale WPI plan: cargo_handling_types is no longer NULL on port %', port_id_value;
                    END IF;

                    UPDATE public.port_constraints
                    SET cargo_handling_types = wpi_cargo,
                        operational_provenance = operational_provenance || jsonb_build_object(field_name, metadata),
                        updated_at = now()
                    WHERE id = constraint_id;
                END IF;

                counts := jsonb_set(
                    counts,
                    '{fill_null}',
                    to_jsonb((counts->>'fill_null')::integer + 1)
                );

            ELSE
                RAISE EXCEPTION 'Unsupported WPI enrichment field: %', field_name;
            END IF;

            counts := jsonb_set(
                counts,
                '{field_actions}',
                to_jsonb((counts->>'field_actions')::integer + 1)
            );
        END LOOP;

        counts := jsonb_set(
            counts,
            '{ports_touched}',
            to_jsonb((counts->>'ports_touched')::integer + 1)
        );
    END LOOP;

    RETURN counts;
END;
$$;

REVOKE ALL ON FUNCTION public.apply_wpi_enrichment(jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.apply_wpi_enrichment(jsonb) FROM anon;
REVOKE ALL ON FUNCTION public.apply_wpi_enrichment(jsonb) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.apply_wpi_enrichment(jsonb) TO service_role;
