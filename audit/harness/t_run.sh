#!/bin/bash
# Test runner: executes one SQL as a given user and prints result/error. Synthetic data only.
q(){ u=$1; shift; echo "### [$u] $*"; if [ "$u" = root ]; then mysql -h127.0.0.1 -P9030 -uroot -e "$*" 2>&1 | head -25; else mysql -h127.0.0.1 -P9030 -u$u -pPassw0rd_Test_1 -e "$*" 2>&1 | grep -v Warning | head -25; fi; echo; }
q root "SELECT current_version()"
q root "SHOW GRANTS FOR ROLE db_admin"
q root "SHOW GRANTS FOR ROLE user_admin"
q root "SHOW GRANTS FOR ROLE security_admin"
q root "SHOW GRANTS FOR ROLE cluster_admin"
q root "SHOW GRANTS FOR ROLE public"
# T-ADM-01 db_admin reads business data
q t_dba "SELECT * FROM biz.clients"
# T-ADM-02 cluster_admin / security_admin direct select (expect deny)
q t_cadm "SELECT * FROM biz.clients"
q t_sec "SELECT * FROM biz.clients"
# T-ADM-03 user_admin self-escalation via GRANT
q t_uadm "SELECT * FROM biz.clients"
q t_uadm "GRANT SELECT ON biz.clients TO USER t_uadm"
q t_uadm "SELECT * FROM biz.clients"
q t_uadm "REVOKE SELECT ON biz.clients FROM USER t_uadm"
q t_uadm "GRANT db_admin TO USER t_uadm"
q t_uadm "GRANT root TO USER t_uadm"
q root "REVOKE db_admin FROM USER t_uadm"
# T-ADM-04 user_admin impersonation of application user
q t_uadm "EXECUTE AS t_app WITH NO REVERT; SELECT * FROM biz.clients"
# T-ADM-05 OPERATE holders: script config state (no script execution)
q t_sec "ADMIN SHOW FRONTEND CONFIG LIKE 'enable_execute_script_on_frontend'"
q t_plain "ADMIN SHOW FRONTEND CONFIG LIKE 'enable_execute_script_on_frontend'"
# T-ADM-06 security_admin / db_admin can manage security integrations & config
q t_sec "SHOW SECURITY INTEGRATIONS"
q t_dba "SHOW SECURITY INTEGRATIONS"
q t_sec "ADMIN SHOW FRONTEND CONFIG LIKE 'authentication_chain'"
# T-PUB public / unprivileged visibility
q t_plain "SELECT * FROM biz.clients"
q t_plain "SELECT TABLE_SCHEMA,TABLE_NAME FROM information_schema.tables WHERE TABLE_SCHEMA='biz'"
q t_plain "SHOW DATABASES"
