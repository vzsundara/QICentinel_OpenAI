-- Original synthetic Snowflake-shaped metadata for the QI Sentinel PoC.
CREATE OR REPLACE MASKING POLICY GOV.PHI_MASK_DOB
  AS (value DATE) RETURNS DATE ->
    CASE
      WHEN CURRENT_ROLE() IN ('SYNTHETIC_PRIVILEGED_ROLE') THEN value
      ELSE DATE_FROM_PARTS(YEAR(value), 1, 1)
    END;

-- Intentional QI-MASK-001 seed: RPT.MEMBER_MEASURE.DOB is tagged in the
-- metadata export but the approved policy is not attached here.
