--Trino
WITH FUNCTION meaning_of_life()
  RETURNS tinyint
  BEGIN
    DECLARE a tinyint DEFAULT CAST(6 as tinyint);
    DECLARE b tinyint DEFAULT CAST(7 as tinyint);
    RETURN a * b;
  END
SELECT meaning_of_life();