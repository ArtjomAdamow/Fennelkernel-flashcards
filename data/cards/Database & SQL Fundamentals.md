# Database & SQL Fundamentals

<details>
  <summary><b> <sd

  What does the standard SQL syntax overview say each core keyword does: `SELECT`, `FROM`, `WHERE`, `GROUP BY`, `HAVING`, `ORDER BY`, `LIMIT`?</b></summary>
  
  `SELECT` returns the final data. `FROM` chooses the base tables. `WHERE` filters the base data. `GROUP BY` aggregates it. `HAVING` filters the aggregated data. `ORDER BY` sorts the final data. `LIMIT` caps the returned row count.  
  Even though `SELECT` is written first, conceptually `FROM` and `WHERE` run first, with `SELECT` and `ORDER BY` near the end.
</details>

<details>
  <summary><b> <sd

  What is the `LIKE` operator used for in a `WHERE` clause?</b></summary>
  
  `LIKE` searches for a pattern in text columns, usually with `%` wildcards, e.g. `WHERE name LIKE 'A%'`.  
  `LIKE` is one of several `WHERE` operators alongside comparison operators, `BETWEEN`, and `IN`.
</details>

<details>
  <summary><b> <sd

  What is the default sort order of `ORDER BY`, and how do you sort by multiple columns?</b></summary>
  
  `ORDER BY` sorts ascending by default; add `DESC` to reverse it.  
  You can sort by multiple columns: `ORDER BY last_name ASC, age DESC`.  
  Columns can also be referenced by index, though names are clearer.
</details>

<details>
  <summary><b> <sd

  What is a database, at its most basic definition?</b></summary>
  
  A systematic collection of data supporting electronic storage and manipulation, either on disk or in memory.  
  Analysts need this because most large-scale data lives in databases and must be queried directly.
</details>

<details>
  <summary><b> <sd

  What do `MIN()`, `MAX()`, `AVG()`, `COUNT()`, and `SUM()` each calculate?</b></summary>
  
  `MIN()` → smallest value  
  `MAX()` → largest value  
  `AVG()` → average  
  `COUNT()` → number of non-NULL values  
  `SUM()` → total  
  `DISTINCT` can be used inside any of them, e.g. `COUNT(DISTINCT column)`.  
  These are typically paired with `GROUP BY` for per-group summaries.
</details>

<details>
  <summary><b> <sd

  In structured, tabular data, what do rows and columns represent?</b></summary>
  
  Rows represent observations; columns represent attributes.  
  Each cell holds exactly one value.
</details>

<details>
  <summary><b> <sd

  Why can't you filter for missing data using `WHERE column_name = NULL`?</b></summary>
  
  `NULL` is the absence of a value, and comparison operators can't evaluate it.  
  Use `IS NULL` or `IS NOT NULL`.  
  A common beginner mistake.
</details>

<details>
  <summary><b> <sd

  What does the `IN` operator do in a `WHERE` clause?</b></summary>
  
  `IN` specifies multiple possible matches, e.g. `WHERE country IN ('Germany','France','Spain')`.  
  It can also accept subqueries: `WHERE customer_id IN (SELECT customer_id FROM vip_customers)`.
</details>

<details>
  <summary><b> <sd

  What does `SELECT * FROM table_name;` do?</b></summary>
  
  Returns all columns and rows. `*` means “all columns”.  
  Explicit column names are usually better than `SELECT *`.
</details>

<details>
  <summary><b> <sd

  What does `SELECT DISTINCT column_name FROM table_name;` return?</b></summary>
  
  Unique values only; duplicates removed.  
  Also usable inside aggregates: `COUNT(DISTINCT column_name)`.
</details>

<details>
  <summary><b> <sd

  How do `AND`, `OR`, and `NOT` behave differently in `WHERE` conditions?</b></summary>
  
  `AND` → all conditions must be TRUE  
  `OR` → at least one must be TRUE  
  `NOT` → invert the condition  
  Example: `WHERE country = 'Germany' AND (age > 18 OR NOT is_minor)`.
</details>

<details>
  <summary><b> <sd

  What is DBeaver, and why is it commonly used to teach SQL?</b></summary>
  
  DBeaver is a free SQL client/IDE for connecting to databases, querying, and visualizing data.  
  Popular because it’s free, easy, and supports many database types.
</details>

<details>
  <summary><b> <sd

  What are the three types of Entity-Relationship cardinality?</b></summary>
  
  One-to-one (1:1)  
  One-to-many (1:n) / many-to-one (n:1)  
  Many-to-many (n:n), usually via a junction table  
  Cardinality determines foreign key placement.
</details>

<details>
  <summary><b> <sd

  What are `DDL`, `DML`, and `DCL`, and how do they differ?</b></summary>
  
  `DDL` → defines schema (create/alter/drop tables)  
  `DML` → manipulates data (`SELECT`, `INSERT`, `UPDATE`, `DELETE`)  
  `DCL` → controls permissions  
  Mnemonic: DDL shapes containers, DML fills them, DCL controls access.
</details>

<details>
  <summary><b> <sd

  Why should you use `LIMIT` when exploring a huge table?</b></summary>
  
  SQL retrieves all rows by default; `LIMIT` keeps exploration fast.  
  Example: `SELECT * FROM table_name LIMIT 10;`
</details>

<details>
  <summary><b> <sd

  What is the difference between a local and a cloud SQL client?</b></summary>
  
  Local client: installed on your machine (e.g., DBeaver).  
  Cloud client: accessed via browser.  
  Both simply connect to a database server.
</details>

<details>
  <summary><b> <sd

  Why do primary and foreign keys matter for avoiding data duplication?</b></summary>
  
  Store a fact once; link to it via foreign keys.  
  JOINs reconstruct relationships.  
  Core principle of relational design.
</details>

<details>
  <summary><b> <sd

  What does creating an alias with the `AS` keyword do?</b></summary>
  
  Gives a temporary name to a column or table within the query.  
  Useful for aggregates, long names, multi-table queries.  
  Convention: snake_case aliases.
</details>

<details>
  <summary><b> <sd

  What are the five basic arithmetic operators in SQL?</b></summary>
  
  `+` addition  
  `-` subtraction  
  `*` multiplication  
  `/` division  
  `%` modulo  
  Example: `SELECT price * 1.19 AS price_incl_tax FROM products;`
</details>

<details>
  <summary><b> <sd

  What is the `WHERE` clause used for, and what operators can it use?</b></summary>
  
  `WHERE` filters rows.  
  Operators: `=`, `>`, `<`, `>=`, `<=`, `<>`, `!=`, `BETWEEN`, `LIKE`, `IN`.  
  `WHERE` filters before grouping; aggregates belong in `HAVING` instead.
</details>

<details>
  <summary><b> <sd

  What are the three core building blocks of the ER model?</b></summary>
  
  Entities, attributes, relationships.  
  ER modeling is conceptual and precedes table creation.
</details>

<details>
  <summary><b> <sd

  Why does `HAVING` exist when `WHERE` already filters data?</b></summary>
  
  Aggregates can't be used in `WHERE`.  
  `HAVING` filters groups *after* `GROUP BY`.  
  Example: `HAVING COUNT(column1) > 5`.
</details>

<details>
  <summary><b> <sd

  What does an `INNER JOIN` return, and is it the default join type?</b></summary>
  
  `INNER JOIN` returns rows matching in both tables.  
  Yes — plain `JOIN` defaults to `INNER JOIN`.  
  Typical ON clause: `ON t1.key = t2.key`.
</details>

<details>
  <summary><b> <sd

  Why does an analyst need to learn SQL and databases?</b></summary>
  
  Most large-scale data lives in databases; analysts must query it directly to extract insights.
</details>

<details>
  <summary><b> <sd

  What are the two ways to write comments in SQL?</b></summary>
  
  Single-line: `-- comment`  
  Multi-line: `/* comment */`  
  Useful for documentation and debugging.
</details>

<details>
  <summary><b> <sd

  Why are SQL keywords like `SELECT` and `FROM` not case sensitive?</b></summary>
  
  SQL treats `select` and `SELECT` identically.  
  Convention: uppercase keywords for readability.
</details>

<details>
  <summary><b> <sd

  What is a primary key, and what is a foreign key?</b></summary>
  
  Primary key: uniquely identifies each record.  
  Foreign key: references a primary key in another table.  
  JOINs match these keys.
</details>

<details>
  <summary><b> <sd

  What does `GROUP BY` do, and what is it usually combined with?</b></summary>
  
  `GROUP BY` groups rows with identical values.  
  Usually combined with aggregates (`MIN`, `MAX`, `AVG`, `COUNT`, `SUM`).  
  Runs after `WHERE` and before `HAVING`.
</details>

<details>
  <summary><b> <sd

  What is the key difference between an RDBMS and a NoSQL database?</b></summary>
  
  RDBMS: SQL, predefined schema, relational tables.  
  NoSQL: flexible/no schema, often document or graph-based.
</details>

<details>
  <summary><b> <sd

  What is the difference between structured, semi-structured, and unstructured data?</b></summary>
  
  Structured: fixed schema (tables).  
  Semi-structured: flexible schema (JSON, CSV).  
  Unstructured: no schema (text, images, audio).
</details>

<details>
  <summary><b> <sd

  What is the structural hierarchy inside a relational database?</b></summary>
  
  Database → schemas → tables → columns & rows.  
  A column is a named variable; a row is one observation; each cell holds one value.
</details>
