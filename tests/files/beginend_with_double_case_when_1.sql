--Trino
WITH FUNCTION double_case(a bigint)
RETURNS varchar
BEGIN
  CASE abs(a)
    WHEN 0 THEN RETURN 'zero';
    WHEN 1 THEN
        CASE
            WHEN a < 0 THEN RETURN 'minus one';
            ELSE RETURN 'one';
        END CASE;
    ELSE RETURN 'other';
  END CASE;
  RETURN null;
END
SELECT double_case(0);
SELECT 1 ;
