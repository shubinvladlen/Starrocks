#!/bin/bash
# T-ADM-09: indirect data-access paths for a custom "DBA without data" role (t_dnd / dba_nodata).
# Expected secure result for every step: no synthetic value (SYNTH_*) is returned to t_dnd.
q(){ u=$1; shift; echo "### [$u] $*"; if [ "$u" = root ]; then mysql -h127.0.0.1 -P9030 -uroot -e "$*" 2>&1 | head -15;
     else mysql -h127.0.0.1 -P9030 -u$u -pPassw0rd_Test_1 -e "SET ROLE ALL; $*" 2>&1 | grep -v Warning | head -15; fi; echo; }

q root "SHOW GRANTS FOR ROLE dba_nodata"
# P1 direct read
q t_dnd "SELECT * FROM biz.clients"
q t_dnd "EXPLAIN SELECT * FROM biz.clients"
# P2 view over business table, then read through view
q t_dnd "CREATE VIEW biz.v_dnd AS SELECT * FROM biz.clients"
q t_dnd "SELECT * FROM biz.v_dnd"
# P3 materialized view
q t_dnd "CREATE MATERIALIZED VIEW biz.mv_dnd REFRESH MANUAL AS SELECT * FROM biz.clients"
# P4 copy via CTAS / INSERT SELECT / CREATE TABLE LIKE
q t_dnd "CREATE TABLE biz.ctas_dnd AS SELECT * FROM biz.clients"
q t_dnd "CREATE TABLE biz.t_dnd_own (id INT, fio VARCHAR(64), card VARCHAR(20)) DUPLICATE KEY(id) DISTRIBUTED BY HASH(id) BUCKETS 1 PROPERTIES('replication_num'='1')"
q t_dnd "INSERT INTO biz.t_dnd_own SELECT * FROM biz.clients"
q t_dnd "SELECT * FROM biz.t_dnd_own"
q t_dnd "CREATE TABLE biz.like_dnd LIKE biz.clients"
# P5 swap own table with business table (privileges are bound to object id, not name)
q t_dnd "ALTER TABLE biz.t_dnd_own SWAP WITH clients_copy"
q t_dnd "SELECT * FROM biz.clients_copy"
q t_dnd "SELECT * FROM biz.t_dnd_own"
# P6 export / backup
q t_dnd "EXPORT TABLE biz.clients TO 'file:///tmp/dnd_export/'"
q t_dnd "CREATE REPOSITORY dnd_repo WITH BROKER ON LOCATION 'file:///tmp/dnd_repo' PROPERTIES()"
q t_dnd "BACKUP SNAPSHOT biz.dnd_snap TO dnd_repo ON (clients)"
# P7 statistics with real values
q t_dnd "ANALYZE TABLE biz.clients"
q t_dnd "SELECT * FROM _statistics_.column_statistics WHERE table_name LIKE '%clients%'"
q t_dnd "SHOW STATS META"
q t_dnd "SHOW HISTOGRAM META"
q t_dnd "SELECT * FROM information_schema.column_stats_usage LIMIT 5"
# P8 metadata derived from data values (automatic list partitioning)
q t_dnd "SHOW PARTITIONS FROM biz.auto_list"
q t_dnd "SELECT PARTITION_NAME FROM information_schema.partitions_meta WHERE TABLE_NAME='auto_list'"
# P9 error messages from schema change on data
q t_dnd "ALTER TABLE biz.clients_copy MODIFY COLUMN fio INT"
q t_dnd "ALTER TABLE biz.clients_copy MODIFY COLUMN card DATE"
sleep 8
q t_dnd "SHOW ALTER TABLE COLUMN FROM biz"
# P10 other users' SQL text (literals)
q t_dnd "SHOW FULL PROCESSLIST"
q t_dnd "SELECT * FROM information_schema.loads LIMIT 3"
# P11 extension paths (privileges absent in role)
q t_dnd "INSTALL PLUGIN FROM '/tmp/nonexistent.zip'"
q t_dnd "CREATE FUNCTION biz.f_dnd(INT) RETURNS INT PROPERTIES('symbol'='x','type'='StarrocksJar','file'='file:///tmp/x.jar')"
q t_dnd "CREATE EXTERNAL CATALOG c_dnd PROPERTIES('type'='jdbc')"
q t_dnd "CREATE FILE 'dnd.pem' PROPERTIES('url'='http://127.0.0.1/x','catalog'='internal')"
q t_dnd "ADMIN SHOW FRONTEND CONFIG LIKE 'enable_execute_script_on_frontend'"
# P12 UDF gate as root (enable_udf=false by default)
q root "CREATE FUNCTION biz.f_root(INT) RETURNS INT PROPERTIES('symbol'='x','type'='StarrocksJar','file'='file:///tmp/x.jar')"
