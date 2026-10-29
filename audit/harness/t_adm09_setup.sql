-- T-ADM-09 setup (run as root). Synthetic data only.
-- Role "DBA without data": object administration without DQL/DML/EXPORT.
CREATE ROLE IF NOT EXISTS dba_nodata;
GRANT CREATE TABLE, CREATE VIEW, CREATE MATERIALIZED VIEW, ALTER, DROP ON ALL DATABASES TO ROLE dba_nodata;
GRANT ALTER, DROP ON ALL TABLES IN ALL DATABASES TO ROLE dba_nodata;
CREATE USER IF NOT EXISTS t_dnd IDENTIFIED BY 'Passw0rd_Test_1' DEFAULT ROLE dba_nodata;
GRANT dba_nodata TO t_dnd;

-- Copy of business table for schema-change error-message check
CREATE TABLE IF NOT EXISTS biz.clients_copy (id INT, fio VARCHAR(64), card VARCHAR(20))
  DUPLICATE KEY(id) DISTRIBUTED BY HASH(id) BUCKETS 1 PROPERTIES("replication_num"="1");
INSERT INTO biz.clients_copy SELECT * FROM biz.clients;

-- Table with automatic list partitioning: partition names are derived from data values
CREATE TABLE IF NOT EXISTS biz.auto_list (id INT, city VARCHAR(32))
  DUPLICATE KEY(id) PARTITION BY (city) DISTRIBUTED BY HASH(id) BUCKETS 1 PROPERTIES("replication_num"="1");
INSERT INTO biz.auto_list VALUES (1,'SYNTH_CITY_ALPHA'),(2,'SYNTH_CITY_BETA');

-- Column statistics (min/max) for biz.clients
ANALYZE FULL TABLE biz.clients WITH SYNC MODE;
