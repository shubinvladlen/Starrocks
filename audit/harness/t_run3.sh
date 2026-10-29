#!/bin/bash
r(){ echo "### [root] $*"; mysql -h127.0.0.1 -P9030 -uroot -e "$*" 2>&1 | head -15; echo; }
# T-AUTH-01 root default password empty
echo "### root login without password:"; mysql -h127.0.0.1 -P9030 -uroot -e "select 'ROOT_EMPTY_PASSWORD_LOGIN_OK'" 2>&1
# T-PWD-01 weak passwords accepted
r "CREATE USER t_weak IDENTIFIED BY '1'"
r "CREATE USER t_nopwd"
# T-PWD-02 expiry / lock syntax
r "ALTER USER t_weak PASSWORD EXPIRE INTERVAL 90 DAY"
r "ALTER USER t_weak ACCOUNT LOCK"
r "CREATE USER t_x IDENTIFIED BY 'abc' PASSWORD_LOCK_TIME 1"
# T-PWD-03 brute force: 10 wrong passwords then correct
for i in $(seq 1 10); do mysql -h127.0.0.1 -P9030 -ut_app -pwrong$i -e "select 1" >/dev/null 2>&1; done
echo "### after 10 failures, correct password:"; mysql -h127.0.0.1 -P9030 -ut_app -pPassw0rd_Test_1 -e "select 'NOT_LOCKED'" 2>&1 | grep -v Warning
# T-TLS-01 SSL state
r "SHOW VARIABLES LIKE '%ssl%'"
r "ADMIN SHOW FRONTEND CONFIG LIKE 'ssl_%'"
r "ADMIN SHOW FRONTEND CONFIG LIKE 'enable_https'"
r "ADMIN SHOW FRONTEND CONFIG LIKE 'enable_http_auth'"
echo "### mysql --ssl-mode=REQUIRED:"; mysql -h127.0.0.1 -P9030 -uroot --ssl-mode=REQUIRED -e "select 1" 2>&1 | head -3
# T-AUD-01 config change via SQL
r "ADMIN SET FRONTEND CONFIG ('qe_slow_log_ms' = '5001')"
r "DROP USER t_nopwd"
r "ALTER TABLE biz.clients SET ('replication_num'='1')"
