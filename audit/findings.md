# findings.md — выявленные нарушения

Версия: StarRocks `4.1.7`, SHA `b81ff9cc465a5f2e5e53104d87a59b349808abd9`. Пути: `FE` = `fe/fe-core/src/main/java/com/starrocks`, `BE` = `be/src`.
Статусы подтверждения: **Доказано (дин.)** — воспроизведено на стенде; **Доказано (стат.)** — однозначно следует из
кода, предусловия подтверждены на стенде, эксплуатация не выполнялась; **Вероятно** — следует из кода, предусловия
не проверены полностью.

Критичность оценена по влиянию на security invariant «администратор СУБД не получает содержимое прикладных данных»
(4.5) и по обязательным требованиям стандарта.

---

## F-01. Встроенная роль `db_admin` имеет полный доступ к прикладным данным, и это нельзя изменить

| Поле | Содержание |
|---|---|
| Требования | 4.5 (в т.ч. встроенные УЗ), 4.11 |
| Критичность | **Критическая.** Стандартная роль администратора СУБД читает любые прикладные данные; роль неизменяема |
| Архитектура | shared-nothing и shared-data (код общий) |
| Исходные привилегии | роль `db_admin` |
| Компонент | FE, RBAC |
| Код | `FE/authorization/AuthorizationMgr.java:194-226` — `initPrivilegeCollectionAllObjects(..., ObjectType.TABLE, provider.getAvailablePrivType(TABLE))` для `*.*.*`, затем `rolePrivilegeCollection.disableMutable()` |
| Root cause | В дизайне встроенных ролей администрирование объектов и доступ к данным совмещены; изменить встроенную роль нельзя (`IMMUTABLE_BUILT_IN_ROLE_NAMES`, `PrivilegeBuiltinConstants.java:43-44`) |
| Цепочка | `GRANT db_admin TO u` → `SET ROLE` / default role → `SELECT * FROM <любая таблица>` / `EXPORT` / `BACKUP` |
| PoC (выполнен) | `harness/t_setup.sql`, `harness/t_run.sh`: `[t_dba] SELECT * FROM biz.clients` → 2 строки синтетических данных (`evidence/t_run.out`) |
| Наблюдаемое / ожидаемое | данные возвращены / доступ должен быть запрещён |
| Компенсирующие меры | не выдавать `db_admin` людям. Создать собственные роли «DBA без данных» из SYSTEM-привилегий и привилегий ALTER/DROP/CREATE без SELECT/EXPORT/INSERT/UPDATE/DELETE. **Но** см. F-02, F-03, F-11: OPERATE, GRANT, SECURITY, PLUGIN дают косвенный путь к данным, поэтому такая роль не обеспечивает инвариант полностью |
| Исправление (вендор) | разделить встроенные роли: «объектный администратор» без DQL/DML/EXPORT; мутируемые встроенные роли или флаг `builtin_roles_data_access=false` |
| Остаточный риск | высокий, пока доступна хотя бы одна из привилегий OPERATE/GRANT/SECURITY/PLUGIN/FILE/REPOSITORY |
| Статус | **Доказано (дин.)** |

## F-02. `user_admin` может выдать себе права на данные и действовать от имени любого пользователя

| Поле | Содержание |
|---|---|
| Требования | 4.5, 4.11 |
| Критичность | **Высокая.** Администратор УЗ становится администратором данных без участия второго лица |
| Исходные привилегии | роль `user_admin` (SYSTEM GRANT, IMPERSONATE ON ALL USERS) |
| Компонент | FE, RBAC |
| Код | `FE/authorization/AuthorizationMgr.java:242-254` (GRANT ON SYSTEM; ALL на USER, включая IMPERSONATE); `FE/sql/analyzer/AuthorizerStmtVisitor.java:1438-1456` — ограничение только для ролей `root` и `cluster_admin`; `:1507-1522` — `GRANT` на любые привилегии при наличии SYSTEM GRANT; `:1358-1370` — `EXECUTE AS` проверяет только IMPERSONATE |
| Root cause | нет запрета самовыдачи и нет принципа «двух лиц»; IMPERSONATE на всех пользователей входит во встроенную роль |
| Цепочка | (a) `GRANT SELECT ON <t> TO USER self` → SELECT; (b) `GRANT db_admin TO USER self`; (c) `EXECUTE AS <app_user> WITH NO REVERT` → SELECT от имени приложения |
| PoC (выполнен) | `harness/t_run2.sh`: все три варианта успешны (`evidence/t_run2.out`). `GRANT root` отклонён: «Can not grant root or cluster_admin role except root user» |
| Аудит | события регистрируются: `Stmt=GRANT ... TO USER t_uadm`, `EXECUTE AS ...`; после EXECUTE AS сохраняются `User=t_uadm|AuthorizedUser='t_app'` (`evidence/audit_log_checks.out`). Это детектируемо, но не предотвращается |
| Компенсирующие меры | не выдавать `user_admin`; собственная роль с GRANT только через PAM с записью сессии; корреляционное правило в ПКБ на GRANT/EXECUTE AS к самому себе |
| Исправление (вендор) | запрет GRANT самому себе; отдельная привилегия IMPERSONATE без включения в `user_admin`; ограничение GRANT по объектам |
| Статус | **Доказано (дин.)** |

## F-03. `ADMIN EXECUTE ON FRONTEND` (Groovy) включён по умолчанию и доступен любому обладателю OPERATE

| Поле | Содержание |
|---|---|
| Требования | 4.5, 4.1 (фактическое совмещение прав СУБД и процесса ОС), 3.3, 5.1/5.5 (возможность обхода аудита) |
| Критичность | **Критическая.** Исполнение произвольного Groovy-кода в JVM FE с объектом `GlobalStateMgr` в binding означает полный контроль над метаданными, RBAC и журналами FE с правами ОС-пользователя процесса FE |
| Исходные привилегии | SYSTEM OPERATE — есть у встроенных `db_admin` и **`security_admin`** |
| Компонент | FE |
| Код | `FE/sql/analyzer/AuthorizerStmtVisitor.java:1373-1383` (`visitExecuteScriptStatement` → только OPERATE); `FE/qe/ExecuteScriptExecutor.java:61-80` (`GroovyShell.evaluate`, binding `globalState`, `metastore`); `FE/common/Config.java:4106-4107` `enable_execute_script_on_frontend = true`, не `mutable` |
| Root cause | отладочная функция включена в production-сборке по умолчанию и защищена эксплуатационной привилегией, а не отдельной |
| Предусловия (проверены) | `ADMIN SHOW FRONTEND CONFIG LIKE 'enable_execute_script_on_frontend'` от `security_admin` → `true`, `IsMutable=false` (`evidence/t_run2.out`); у `t_plain` без OPERATE — Access denied |
| PoC | **не выполнялся** (методологическое ограничение, см. audit_scope.md §4). Безопасная проверка для заказчика описана в test_plan.md `T-ADM-05`: убедиться, что после `enable_execute_script_on_frontend=false` оператор возвращает «execute script on frontend is disabled» |
| BE-вариант | `ADMIN EXECUTE ON <be_id>` → `ExecuteScriptExecutor.java:82-` → BRPC `execute_command`; на BE — Wren-скрипт с белым списком привязок, `exec` закомментирован (`BE/script/script.cpp:235`). Значительно ниже по риску, но флага отключения нет |
| Компенсирующие меры | в `fe.conf` задать `enable_execute_script_on_frontend = false` (требует рестарта FE); не выдавать OPERATE людям без PAM |
| Исправление (вендор) | `false` по умолчанию; отдельная привилегия; регистрация в аудите текста скрипта (сейчас — только как Stmt) |
| Статус | **Доказано (стат.)**, предусловия подтверждены динамически |

## F-04. Встроенная УЗ `root`: пустой пароль по умолчанию, неудаляема, обходит Ranger

| Поле | Содержание |
|---|---|
| Требования | 4.2, 4.3, 4.5 |
| Критичность | **Высокая** (до смены пароля — критическая: аутентификации фактически нет) |
| Код | `FE/authentication/AuthenticationMgr.java:113-116` (`new UserAuthenticationInfo(UserRef.ROOT, null)`); `FE/authorization/AuthorizationMgr.java:280-284`; `FE/authorization/ranger/RangerAccessController.java:161-164` (`if (UserIdentity.ROOT.equals(user)) return;`); `AuthorizerStmtVisitor.visitRevokeRoleStatement` — запрет отзыва роли root у root |
| PoC (выполнен) | `mysql -uroot` без пароля → `ROOT_EMPTY_PASSWORD_LOGIN_OK` (`evidence/t_run3.out`) |
| Ограничения | root нельзя заблокировать (механизма блокировки нет, F-05) и нельзя лишить прав; при Ranger root не контролируется политиками |
| Компенсирующие меры | сменить пароль при развёртывании; хранить его в PAM (сейф); ограничить вход `root` сетевым ACL / `CREATE USER root@'<pam_host>'` — проверить на стенде заказчика (H-07) |
| Статус | **Доказано (дин.)** — пустой пароль; **Доказано (стат.)** — Ranger bypass |

## F-05. Нет парольной политики и блокировки учётных записей

| Поле | Содержание |
|---|---|
| Требования | 4.8 (12/330, 16/90), 4.2 (блокировка неиспользуемых УЗ), 5.1 (события блокировки/разблокировки) |
| Критичность | **Высокая** |
| Код | грамматика `fe/fe-grammar/.../StarRocks.g4:1823-1835` — у `CREATE/ALTER USER` нет `PASSWORD EXPIRE`, `ACCOUNT LOCK`, `FAILED_LOGIN_ATTEMPTS`; `FE/sql/analyzer/UserAuthOptionAnalyzer.java` проверяет только формат хэша; хранение — MySQL native: двойной SHA-1 без соли (`FE/mysql/MysqlPassword.java:130,154`) |
| PoC (выполнен) | `CREATE USER t_weak IDENTIFIED BY '1'` — OK; `CREATE USER t_nopwd` — OK; `PASSWORD EXPIRE`, `ACCOUNT LOCK`, `PASSWORD_LOCK_TIME` — синтаксическая ошибка; 10 неверных паролей подряд → вход с верным паролем успешен (`evidence/t_run3.out`) |
| Компенсирующие меры | использовать только внешнюю аутентификацию (LDAP/СУДИР) с политиками на стороне IdP; для native-УЗ — PAM-ротация; отслеживать неуспешные входы в ПКБ (сначала включить их регистрацию, см. F-07) |
| Неустранимо конфигурацией | да, для native-УЗ |
| Статус | **Доказано (дин.)** |

## F-06. Административные HTTP-эндпоинты BE доступны анонимно по умолчанию; изменения не аудируются

| Поле | Содержание |
|---|---|
| Требования | 4.3, 4.4, 5.1 (изменение конфигурации), 5.5 (доступ к журналам) |
| Критичность | **Высокая** |
| Код | `BE/common/config.h:737` `enable_http_auth=false`; `BE/service/service_be/http_auth_response.cpp:94-97` (`if (!config::enable_http_auth) return std::nullopt;`); `BE/http/action/update_config_action.h:59`, `greplog_action.h:32`, `pprof_actions.h:44` (требуют OPERATE **только** при включённой аутентификации) |
| PoC (выполнен, безопасный) | `POST :8040/api/update_config?report_task_interval_seconds=11` без учётных данных → `{"status":"OK"}`; `/varz` показал новое значение; возвращено к 10. Записей в `fe.audit.log` — 0 (`evidence/http_checks.out`). `/greplog`, `/varz`, `/metrics`, `/api/compaction/show` → 200 анонимно |
| Компенсирующие меры | `enable_http_auth = true` в `be.conf` **и** `fe.conf` (immutable, рестарт); сетевой ACL на 8040 только для FE/BE и PAM; `enable_https=true`, иначе Basic-пароль передаётся открыто |
| Ограничение меры | stream load и download остаются без Basic-проверки по дизайну (`stream_load.h:70`, `download_action.h:44`) |
| Статус | **Доказано (дин.)** |

## F-07. Неполнота штатного аудита относительно 5.1/5.2

| Поле | Содержание |
|---|---|
| Требования | 5.1, 5.2 |
| Критичность | **Высокая** (требования аудита не выполняются в конфигурации по умолчанию, часть — ни в какой) |
| Код и факты | (1) `FE/common/Config.java:171` `audit_log_modules = {"slow_query","query"}`; запись входов — только при модуле `connection` (`FE/common/util/LogUtil.java:40-52`), параметр immutable. (2) `AuditEvent.EventType.DISCONNECTION` (`FE/plugin/AuditEvent.java:66`) объявлен, но нигде не генерируется → **выход пользователя не регистрируется**. (3) В `AuditEvent` нет поля приложения: connect attrs разбираются (`FE/mysql/MysqlAuthPacket.java:126-127`), но не пишутся → атрибут 5.2 «приложение» отсутствует. (4) `/api/_set_config` (FE) меняет конфигурацию без записи в аудит (`FE/http/rest/SetConfigAction.java:76-100`, только `LOG.debug`). (5) BE `update_config` — то же (F-06). (6) Блокировка/разблокировка УЗ невозможны (F-05) → регистрировать нечего. (7) Неуспешные HTTP Basic-входы на FE пишутся только в `fe.log` (`BaseAction.checkPassword` → `AccessDeniedException`) |
| PoC (выполнен) | при настройках по умолчанию: записей `[connection]` — 0; 10 неуспешных входов `t_app` — 0 записей; DDL/DCL/`ADMIN SET CONFIG` — регистрируются как `[query]` (`evidence/audit_log_checks.out`) |
| Что соответствует | создание/удаление УЗ, GRANT/REVOKE, ALTER USER, DDL объектов, `ADMIN SET FRONTEND CONFIG`, SELECT/DML (доступ к объектам) — фиксируются со `User`, `AuthorizedUser`, `Client` (IP:port), `Timestamp`, `feIp`, `Stmt`, `State`; пароли маскируются (`IDENTIFIED BY '***'`) |
| Компенсирующие меры | `audit_log_modules = slow_query, query, connection`; DAM-агент (5.6) для выхода из сессии и имени приложения; запрет HTTP set_config сетевым ACL |
| Статус | **Доказано (дин.)** для (1),(4 — стат.),(5),(6),(7 — стат.); **Доказано (стат.)** для (2),(3) |

## F-08. Анонимные HTTP-эндпоинты FE раскрывают метаданные

| Поле | Содержание |
|---|---|
| Требования | 4.3 |
| Критичность | **Средняя** |
| Код | `FE/common/Config.java:932` `enable_http_auth=false`; эндпоинты с `needAuth(){return Config.enable_http_auth;}`: `ShowDataAction`, `ShowMetaInfoAction`, `ShowRuntimeInfoAction`, `MetricsAction` и др. |
| PoC (выполнен) | `/api/show_meta_info?action=SHOW_DB_SIZE` → имена всех БД; `/metrics` → 66 КБ метрик (`evidence/http_checks.out`). Профили и query_detail требуют аутентификацию (401) |
| Мера | `enable_http_auth=true` (рестарт FE) |
| Статус | **Доказано (дин.)** |

## F-09. Внутренние каналы кластера без TLS и без взаимной аутентификации узлов

| Поле | Содержание |
|---|---|
| Требования | 2.4 |
| Критичность | **Высокая** (архитектурное ограничение) |
| Факты | Thrift FE↔BE (9020/9060): TLS не реализован — в FE и BE нет `TSSL*`. BDB JE (9010): SSL-параметры репликации не задаются (`journal/bdbje`). BRPC (8060): TLS только при BE `enable_https=true` (`BE/service/service_be/starrocks_be.cpp:204-207`, сертификат сервера, без проверки клиента), по умолчанию выкл. (`BE/common/config.h:52`). Аутентификации вызывающего узла на BRPC/Thrift BackendService нет. Arrow Flight BE: «Not authenticated in BE flight server» (`BE/service/service_be/arrow_flight_sql_service.cpp:45`), по умолчанию выключен (`arrow_flight_port=-1`) |
| Последствие | данные результатов и фрагментов, cluster token и метаданные передаются открытым текстом; BE доверяет любому сетевому отправителю в TB1. Авторизация FE не действует для запросов, отправленных напрямую в BE (свойство архитектуры, эксплуатация не выполнялась) |
| Компенсирующие меры | выделенный сегмент/VLAN для межузлового трафика, ACL «только узлы кластера», шифрование на уровне инфраструктуры (IPsec/WireGuard/service mesh mTLS). Это **внешний** контроль, а не возможность StarRocks |
| Неустранимо конфигурацией | да, для Thrift и BDB JE |
| Статус | **Доказано (стат.)**; дин.: `/varz` → `enable_https=false` |

## F-10. TLS клиентского протокола не принудителен; параметры TLS зависят от JDK

| Поле | Содержание |
|---|---|
| Требования | 2.4 |
| Критичность | **Средняя** (устраняется конфигурацией при условии контроля JDK) |
| Код | `FE/mysql/ssl/SSLContextLoader.java:36-41` (TLS только при `ssl_keystore_location`); `:51-55` — включаются **все** поддерживаемые JDK протоколы (`getSupportedSSLParameters`); минимальная версия в коде не задана. `SSLContext.getInstance("TLSv1.2")` (`:67`) задаёт только реализацию. `FE/mysql/MysqlProto.java:129-139` — `ssl_force_secure_transport` (по умолчанию `false`) не действует для localhost. mTLS не поддерживается (нет `setNeedClientAuth`) |
| PoC (выполнен) | по умолчанию `--ssl-mode=REQUIRED` → «server doesn't support it». С тестовым keystore: TLS 1.0/1.1 → alert 70 (благодаря `jdk.tls.disabledAlgorithms` JDK 17); TLS 1.2 принимает в т.ч. CBC-наборы с SHA-1 (`ECDHE-RSA-AES128-SHA` и др.); TLS 1.3 — 3 AEAD-набора; plaintext-подключение при этом по-прежнему разрешено (`evidence/tls_ciphers.out`) |
| Компенсирующие меры | `ssl_keystore_*`, `ssl_force_secure_transport=true`, `ssl_cipher_whitelist` = AEAD-наборы из /6/; JDK с запретом TLSv1/1.1 в `java.security`; FE `enable_https=true` и закрыть 8030 |
| Зависимость | перечень разрешённых алгоритмов /6/ не приложен — соответствие наборов не оценено |
| Статус | **Доказано (дин.)** |

## F-11. Привилегия SECURITY позволяет администратору управлять источником идентичности

| Поле | Содержание |
|---|---|
| Требования | 4.3, 4.5 |
| Критичность | **Высокая** (вероятная) |
| Код | `AuthorizerStmtVisitor.java:1590-1700` (CREATE/ALTER SECURITY INTEGRATION, GROUP PROVIDER → SECURITY); `FE/common/Config.java:2317-2318` `authentication_chain` — mutable, меняется `ADMIN SET FRONTEND CONFIG` (OPERATE); `FE/authentication/AuthenticationHandler.java` — пользователи из integration создаются как ephemeral, роли выводятся из групп. SECURITY есть у `db_admin` (`AuthorizationMgr.java:209`) и `security_admin` |
| Риск | администратор с SECURITY+OPERATE может подключить подконтрольный IdP и выпускать внешние идентичности с группами, сопоставленными ролям. При Ranger авторизация идёт по имени пользователя/группам, что расширяет последствия |
| Проверено | `security_admin` видит и может менять `authentication_chain` (`IsMutable=true`, `evidence/t_run2.out`). Создание integration не выполнялось |
| Дополнительно | LDAP по умолчанию без TLS: `authentication_ldap_simple_ssl_conn_allow_insecure = true` (`Config.java:2359`) → `ldap://`, пароль пользователя передаётся FE открыто (`LDAPAuthProvider.getURL`) |
| Меры | SECURITY/OPERATE — только через PAM и принцип двух лиц; мониторинг `CREATE/ALTER SECURITY INTEGRATION` и `ADMIN SET ... authentication_chain` в ПКБ; `authentication_ldap_simple_ssl_conn_allow_insecure=false` + truststore |
| Статус | **Вероятно** |

## F-12. Хранение и защита журналов аудита зависят от ОС; администратор СУБД может влиять на аудит

| Поле | Содержание |
|---|---|
| Требования | 5.3, 5.4, 5.5 |
| Критичность | **Средняя** |
| Факты | `audit_log_delete_age = "30d"` (`Config.java:181`) — короче календарного месяца в 31 день; `log_cleaner_audit_log_min_retention_days = 3` при `log_cleaner_disk_util_based_enable=true` (по умолч. `false`). Встроенной отправки в ПКБ/syslog нет — только файл `fe.audit.log` (+ опц. плагин AuditLoader в таблицу StarRocks). В официальном образе allin1 FE работает от root, журнал `-rw-r--r--` (0644). Администратор с OPERATE (F-03) или PLUGIN (`UNINSTALL PLUGIN`) влияет на сбор/хранение аудита. Аудит BE-операций (HTTP/BRPC) отсутствует |
| Меры | `audit_log_delete_age = 35d` или больше; отправка `fe.audit.log` агентом (filebeat/rsyslog) в ПКБ в реальном времени; права 0600, отдельный ОС-пользователь; неизменяемое внешнее хранилище |
| Статус | **Доказано (дин.)** для прав и сроков; остальное — **стат.** |

## F-13. Прочие косвенные пути доступа к данным у административных привилегий (гипотезы высокого приоритета)

Не подтверждены динамически, детали — в hypotheses.md: PLUGIN (`INSTALL PLUGIN` = загрузка кода в FE),
CREATE_GLOBAL_FUNCTION (Java UDF; `enable_udf=false` по умолчанию), REPOSITORY+EXPORT (BACKUP во внешнее
хранилище), FILE, CREATE_EXTERNAL_CATALOG/RESOURCE (выгрузка через внешние системы), NODE (изменение состава
кластера). Статус: **Вероятно / Не подтверждено**.

---

## Сводка

| ID | Название | Требования | Критичность | Статус |
|---|---|---|---|---|
| F-01 | `db_admin` читает все данные, роль неизменяема | 4.5, 4.11 | Критическая | Доказано (дин.) |
| F-03 | Groovy `ADMIN EXECUTE` по OPERATE, включено по умолч. | 4.5, 4.1, 3.3 | Критическая | Доказано (стат.) |
| F-02 | `user_admin`: самовыдача прав и IMPERSONATE | 4.5, 4.11 | Высокая | Доказано (дин.) |
| F-04 | `root`: пустой пароль, обход Ranger | 4.2, 4.3, 4.5 | Высокая | Доказано (дин./стат.) |
| F-05 | Нет парольной политики и блокировки | 4.8, 4.2, 5.1 | Высокая | Доказано (дин.) |
| F-06 | Анонимные admin-эндпоинты BE, без аудита | 4.3, 5.1, 5.5 | Высокая | Доказано (дин.) |
| F-07 | Неполнота аудита (вход/выход/отказ/приложение/HTTP-конфиг) | 5.1, 5.2 | Высокая | Доказано |
| F-09 | Межузловые каналы без TLS и аутентификации | 2.4 | Высокая | Доказано (стат.) |
| F-11 | SECURITY = управление IdP | 4.3, 4.5 | Высокая | Вероятно |
| F-08 | Анонимные метаданные FE HTTP | 4.3 | Средняя | Доказано (дин.) |
| F-10 | TLS клиента не принудителен, зависит от JDK | 2.4 | Средняя | Доказано (дин.) |
| F-12 | Хранение/защита журналов | 5.3–5.5 | Средняя | Доказано (частично) |
| F-13 | Косвенные пути через PLUGIN/UDF/BACKUP/NODE | 4.5 | — | Гипотезы |
