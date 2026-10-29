#!/bin/bash
# Part 1: verify hardened config (run inside container). Synthetic data only.
echo "=== T-TLS-04: ssl_force_secure_transport=true ==="
echo "-- plaintext from external-looking addr (via container IP), ssl-mode=DISABLED:"
CIP=$(hostname -i | awk '{print $1}')
mysql -h$CIP -P9030 -uroot --ssl-mode=DISABLED -e "select 'PLAINTEXT_EXTERNAL_OK'" 2>&1 | grep -v Warning | tail -2
echo "-- plaintext from 127.0.0.1 (localhost exemption), ssl-mode=DISABLED:"
mysql -h127.0.0.1 -P9030 -uroot --ssl-mode=DISABLED -e "select 'PLAINTEXT_LOCALHOST_OK'" 2>&1 | grep -v Warning | tail -2
echo "-- TLS from external addr, ssl-mode=REQUIRED:"
mysql -h$CIP -P9030 -uroot --ssl-mode=REQUIRED -e "select 'TLS_EXTERNAL_OK'" 2>&1 | grep -v Warning | tail -2

echo; echo "=== T-HTTP-04: enable_http_auth=true (FE 8030) ==="
for p in /api/show_meta_info?action=SHOW_DB_SIZE /metrics /api/show_data; do
  printf "anon   %-40s " "$p"; curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8030$p"
done
printf "t_plain %-40s " "/api/_set_config?qe_slow_log_ms=5003"; curl -s -o /dev/null -w "%{http_code}\n" -u t_plain:Passw0rd_Test_1 "http://127.0.0.1:8030/api/_set_config?qe_slow_log_ms=5003"
printf "root    %-40s " "/api/show_meta_info"; curl -s -o /dev/null -w "%{http_code}\n" -u root: "http://127.0.0.1:8030/api/show_meta_info?action=SHOW_DB_SIZE"

echo; echo "=== T-HTTP-04: enable_http_auth=true (BE 8040) ==="
for p in /varz /metrics "/api/update_config?report_task_interval_seconds=12" /greplog?pattern=x; do
  printf "anon   %-45s " "$p"; curl -s -X POST -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8040$p"
done
printf "t_plain %-45s " "/api/update_config (no OPERATE)"; curl -s -X POST -o /dev/null -w "%{http_code}\n" -u t_plain:Passw0rd_Test_1 "http://127.0.0.1:8040/api/update_config?report_task_interval_seconds=12"
printf "root    %-45s " "/varz"; curl -s -o /dev/null -w "%{http_code}\n" -u root: "http://127.0.0.1:8040/varz"
echo "report_task_interval_seconds now: $(curl -s -u root: http://127.0.0.1:8040/varz | grep '^report_task_interval_seconds=')"

echo; echo "=== T-ADM-05: Groovy disabled ==="
mysql -h127.0.0.1 -P9030 -uroot --ssl-mode=PREFERRED -e "ADMIN EXECUTE ON FRONTEND 'out.append(1+1)'" 2>&1 | grep -v Warning | tail -2
