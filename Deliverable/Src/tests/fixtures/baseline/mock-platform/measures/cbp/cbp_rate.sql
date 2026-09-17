-- Clean original synthetic measure logic for the QI Sentinel PoC.
WITH hypertension_members AS (
    SELECT member_key
    FROM synthetic_value_set('VS_HYPERTENSION', '2026')
),
eligible_members AS (
    SELECT member_key
    FROM synthetic_measure_population
    WHERE exclusion_reason NOT IN ('HOSPICE_ENCOUNTER', 'PALLIATIVE_CARE')
)
SELECT eligible.member_key
FROM eligible_members AS eligible
INNER JOIN hypertension_members AS value_set
    ON value_set.member_key = eligible.member_key;
