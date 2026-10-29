# test_plan.md — воспроизводимые тесты

## 1. Harness

| Элемент | Значение |
|---|---|
| Образ | `starrocks/allin1-ubuntu:4.1.7` (`current_version()` = `4.1.7-b81ff9c`) |
| Хост | Linux, Docker 29.x; на macOS — Docker Desktop, те же команды |
| Тестовые данные | только синтетические: `biz.clients` (2 строки `SYNTH_*`) — `harness/t_setup.sql` |
| Ролевая модель | `t_dba`(db_admin), `t_uadm`(user_admin), `t_sec`(security_admin), `t_cadm`(cluster_admin), `t_app`(SELECT на biz.clients), `t_plain`(без прав); пароль `Passw0rd_Test_1` (только стенд) |
| Скрипты | `harness/t_run.sh`, `t_run2.sh` (роли с `SET ROLE ALL`), `t_run3.sh` (аутентификация, TLS-состояние, аудит) |
| Результаты | `evidence/*.out` |

Запуск стенда (если `ulimit -n` хоста < 60000, понизить порог BE):

```bash
docker run -d --name sr417 --ulimit nofile=20000:20000 -p 9030:9030 -p 8030:8030 -p 8040:8040 --entrypoint bash starrocks/allin1-ubuntu:4.1.7 -c 'echo "min_file_descriptor_number = 10000" >> /data/deploy/starrocks/be/conf/be.conf; exec /usr/bin/tini-static -- ./entrypoint.sh'
```

```bash
docker cp harness/t_setup.sql sr417:/tmp/ && docker exec sr417 bash -c 'mysql -h127.0.0.1 -P9030 -uroot < /tmp/t_setup.sql'
```

```bash
for s in t_run.sh t_run2.sh t_run3.sh; do docker cp harness/$s sr417:/tmp/ && docker exec sr417 bash /tmp/$s; done
```

Ограничение: тесты не разрушающие, выполнять только на изолированном стенде. Тест T-HTTP-03 меняет параметр BE и возвращает его.

## 2. Тест-кейсы

| ID | Требование | Шаги | Ожидаемое безопасное поведение | Факт (4.1.7, по умолч.) | Статус |
|---|---|---|---|---|---|
| T-ROLE-01 | 4.10, 4.11 | `SHOW GRANTS FOR ROLE db_admin/user_admin/security_admin/cluster_admin/public` | роли без доступа к данным | db_admin: SELECT/EXPORT ON ALL TABLES; user_admin: GRANT + IMPERSONATE ON ALL USERS | выполнен |
| T-ADM-01 | 4.5 | `t_dba`: `SELECT * FROM biz.clients` | отказ | данные возвращены | выполнен, **НС** |
| T-ADM-02 | 4.5 | `t_sec`, `t_cadm`: `SELECT` | отказ | отказ | выполнен, С |
| T-ADM-03 | 4.5 | `t_uadm`: `GRANT SELECT ... TO USER t_uadm` / `GRANT db_admin TO USER t_uadm` → `SELECT` | отказ самовыдачи | успешно | выполнен, **НС** |
| T-ADM-04 | 4.5 | `t_uadm`: `EXECUTE AS t_app WITH NO REVERT; SELECT` | отказ | успешно; аудит: `User=t_uadm, AuthorizedUser=t_app` | выполнен, **НС** |
| T-ADM-05 | 4.5, 3.3 | `ADMIN SHOW FRONTEND CONFIG LIKE 'enable_execute_script_on_frontend'` от `t_sec` | `false` | `true`, immutable | выполнен (предусловие). **Для заказчика**: после `enable_execute_script_on_frontend=false` и рестарта FE выполнить `ADMIN EXECUTE ON FRONTEND 'out.append(1)'` → ожидать «execute script on frontend is disabled» |
| T-ADM-06 | 4.3, 4.5 | `t_sec`: `ADMIN SHOW FRONTEND CONFIG LIKE 'authentication_chain'` | нет права менять источник аутентификации без 2-го лица | `IsMutable=true`, доступно | выполнен |
| T-ADM-07 | 5.1 | `t_dba`: `ADMIN SHOW FRONTEND CONFIG LIKE 'audit_log_%'` | — | `audit_log_modules=[slow_query, query]`, immutable | выполнен |
| T-ADM-08 | 4.5 | `t_cadm`: `SELECT`, `SHOW BACKENDS` | SELECT — отказ | отказ; SHOW BACKENDS — OK | выполнен |
| T-ADM-09 | 4.5 | **Для заказчика**: роль `dba_nodata` = `CREATE TABLE, ALTER, DROP ON ALL DATABASES` + `ALTER, DROP ON ALL TABLES` без SELECT/EXPORT/INSERT; проверить SELECT, `EXPORT`, `BACKUP`, `CREATE VIEW ... AS SELECT` + `SELECT` из своей view, `CREATE MATERIALIZED VIEW` + `REFRESH` + `SELECT` | все пути к данным — отказ | — | не выполнен |
| T-PUB-01 | 4.12 | `t_plain`: `SELECT ... FROM information_schema.tables WHERE TABLE_SCHEMA='biz'`; `SHOW DATABASES` | объекты без прав не видны | пусто; только `information_schema` | выполнен, С |
| T-AUTH-01 | 4.2, 4.3 | `mysql -uroot` без пароля на свежем экземпляре | отказ / принудительная смена | вход успешен | выполнен, **НС** |
| T-PWD-01 | 4.8 | `CREATE USER t_weak IDENTIFIED BY '1'`; `CREATE USER t_nopwd` | отказ | успешно | выполнен, **НП** |
| T-PWD-02 | 4.8, 4.2 | `ALTER USER ... PASSWORD EXPIRE INTERVAL 90 DAY`, `ACCOUNT LOCK`, `PASSWORD_LOCK_TIME` | поддерживается | синтаксическая ошибка | выполнен, **НП** |
| T-PWD-03 | 4.8 | 10 неверных паролей `t_app`, затем верный | блокировка | вход успешен | выполнен, **НП** |
| T-TLS-01 | 2.4 | по умолчанию `mysql --ssl-mode=REQUIRED` | TLS | «server doesn't support it» | выполнен, **НС** |
| T-TLS-02 | 2.4 | keystore (`keytool -genkeypair ... -storetype JKS`) + `ssl_keystore_*` в fe.conf, рестарт FE; `--ssl-mode=REQUIRED` и `--ssl-mode=DISABLED` | TLS OK; plaintext — отказ при `ssl_force_secure_transport=true` | TLS OK; plaintext OK (force=false) | выполнен |
| T-TLS-03 | 2.4 | `openssl s_client -starttls mysql -connect :9030 -tls1/-tls1_1 -cipher DEFAULT@SECLEVEL=0`; перебор наборов TLS 1.2/1.3 со строгим сравнением | ≤ TLS1.1 — отказ; только наборы из /6/ | TLS1.0/1.1 — alert 70; TLS1.2 — 14 наборов (в т.ч. CBC-SHA1); TLS1.3 — 3 | выполнен (`evidence/tls_ciphers.out`) |
| T-TLS-04 | 2.4 | **Для заказчика**: `ssl_force_secure_transport=true`, `ssl_cipher_whitelist=<AEAD из /6/>`; повторить T-TLS-02/03; подключиться с `-h127.0.0.1` без TLS | plaintext с localhost — отказ | ожидается: разрешено (`MysqlProto.java:130-138`) | не выполнен |
| T-TLS-05 | 2.4 | **Для заказчика**: `tcpdump` на 9020/9060/8060/9010 при выполнении SELECT | шифрованный трафик | ожидается plaintext (F-09) | не выполнен |
| T-HTTP-01 | 4.3 | анонимный GET к FE 8030: show_data, show_meta_info, show_runtime_info, metrics, query_detail, profile, _set_config | 401 | 200 для show_*/metrics; 401 для query_detail/profile/_set_config | выполнен (`evidence/http_checks.out`) |
| T-HTTP-02 | 4.3, 5.5 | анонимный GET к BE 8040: varz, greplog, metrics, compaction/show, `_tablet/_download` без token | 401 | 200, кроме download («token is not specified.») | выполнен |
| T-HTTP-03 | 4.3, 5.1 | анонимный `POST /api/update_config?report_task_interval_seconds=11`, проверка `/varz`, возврат 10; grep в fe.audit.log и be.INFO | 401; событие в аудите | применено; 0 записей | выполнен, **НС** |
| T-HTTP-04 | 4.3 | **Для заказчика**: `enable_http_auth=true` в fe.conf и be.conf, рестарт; повторить T-HTTP-01..03 | 401 без Basic; 403 без OPERATE | — | не выполнен |
| T-AUD-01 | 5.1 | `grep -c "\[connection\]" fe.audit.log` | > 0 | 0 | выполнен, **НС** |
| T-AUD-02 | 5.1 | 10 неуспешных входов → поиск в fe.audit.log | записи с отказом | 0 | выполнен, **НС** |
| T-AUD-03 | 5.1 | CREATE/DROP USER, GRANT/REVOKE, ADMIN SET CONFIG, ALTER TABLE → поиск Stmt | записи есть, пароль скрыт | есть, `'***'` | выполнен, С |
| T-AUD-04 | 5.1, 5.2 | **Для заказчика**: `audit_log_modules = slow_query, query, connection`; повторить T-AUD-01/02, проверить, что при выходе `quit` нет записи | вход/отказ — есть; выход — нет | — | не выполнен |
| T-AUD-05 | 5.2 | поля записи `[query]` | user, app, event, time, source | нет «приложения» | выполнен |
| T-AUD-06 | 5.5 | `stat` fe.audit.log | 0600, не root | allin1: root 0644 | выполнен |
| T-AUTHZ-02 | 4.11 | **Для заказчика**: сессия `t_app` открыта; root делает `REVOKE SELECT`; повторить SELECT в той же сессии | отказ сразу | — | не выполнен (H-24) |
