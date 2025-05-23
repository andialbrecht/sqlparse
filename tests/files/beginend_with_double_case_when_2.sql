--Trino
WITH FUNCTION double_case(a bigint)
RETURNS varchar
BEGIN
  RETURN
    CASE abs(a)
      WHEN 0 THEN 'zero'
      WHEN 1 THEN
          CASE
              WHEN a < 0 THEN 'minus one'
              ELSE 'one'
          END
      ELSE 'other'
    END;
END
SELECT double_case(0);
SELECT 1 ;
