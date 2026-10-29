#!/bin/bash
# T-ADM-09 (part 2): schema-change error messages, EXPORT/BACKUP authorization with valid syntax.
q(){ u=$1; shift; echo "### [$u] $*"; mysql -h127.0.0.1 -P9030 -u$u -pPassw0rd_Test_1 -e "SET ROLE ALL; $*" 2>&1 | grep -v Warning | head -12; echo; }
q t_dnd "ALTER TABLE biz.clients_copy MODIFY COLUMN fio INT"
sleep 12
q t_dnd "SHOW ALTER TABLE COLUMN FROM biz WHERE TableName='clients_copy'"
echo "### [root] SELECT * FROM biz.clients_copy"; mysql -h127.0.0.1 -P9030 -uroot -e "SELECT * FROM biz.clients_copy"; echo
q t_dnd "EXPORT TABLE biz.clients TO 's3://dnd-bucket/export/' PROPERTIES('column_separator'=',') WITH BROKER ('aws.s3.access_key'='x','aws.s3.secret_key'='y','aws.s3.endpoint'='http://127.0.0.1:1','aws.s3.region'='us-east-1')"
q t_dnd "CREATE REPOSITORY dnd_repo WITH BROKER ON LOCATION 's3://dnd-bucket/repo' PROPERTIES('aws.s3.access_key'='x','aws.s3.secret_key'='y','aws.s3.endpoint'='http://127.0.0.1:1','aws.s3.region'='us-east-1')"
q t_dnd "CREATE FILE 'dnd.pem' IN biz PROPERTIES('url'='http://127.0.0.1:1/x','catalog'='internal')"
