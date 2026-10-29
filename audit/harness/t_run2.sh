#!/bin/bash
q(){ u=$1; shift; echo "### [$u] $*"; mysql -h127.0.0.1 -P9030 -u$u -pPassw0rd_Test_1 -e "SET ROLE ALL; $*" 2>&1 | grep -v Warning | head -20; echo; }
# T-ADM-03 user_admin: self-grant of data privilege
q t_uadm "GRANT SELECT ON biz.clients TO USER t_uadm"
q t_uadm "SELECT * FROM biz.clients"
q t_uadm "REVOKE SELECT ON biz.clients FROM USER t_uadm"
# T-ADM-03b user_admin: self-grant of db_admin role
q t_uadm "GRANT db_admin TO USER t_uadm"
q t_uadm "SELECT count(*) FROM biz.clients"
mysql -h127.0.0.1 -P9030 -uroot -e "REVOKE db_admin FROM USER t_uadm"
# T-ADM-04 user_admin impersonation
q t_uadm "EXECUTE AS t_app WITH NO REVERT; SELECT count(*) FROM biz.clients"
# T-ADM-05 OPERATE holders see script flag (no script is executed)
q t_sec "ADMIN SHOW FRONTEND CONFIG LIKE 'enable_execute_script_on_frontend'"
q t_sec "ADMIN SHOW FRONTEND CONFIG LIKE 'authentication_chain'"
q t_sec "SHOW SECURITY INTEGRATIONS"
q t_sec "SELECT * FROM biz.clients"
# T-ADM-07 db_admin can disable/alter audit-related runtime config
q t_dba "ADMIN SHOW FRONTEND CONFIG LIKE 'audit_log_%'"
q t_dba "ADMIN SHOW FRONTEND CONFIG LIKE 'enable_audit_sql'"
# T-ADM-08 cluster_admin
q t_cadm "SELECT * FROM biz.clients"
q t_cadm "SHOW BACKENDS\G" 
