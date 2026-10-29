# architecture.md — архитектура безопасности, доверительные границы, поверхность атаки

Пути указаны относительно корня upstream-репозитория на SHA `b81ff9cc`.
`FE` = `fe/fe-core/src/main/java/com/starrocks`, `BE` = `be/src`.

## 1. Компоненты

| Компонент | Роль | Хранимые данные |
|---|---|---|
| FE Leader/Follower/Observer (Java) | парсинг, анализ, авторизация, планирование, метаданные, RBAC, аудит | BDB JE (`meta/bdb`), image, `fe.audit.log`, `fe.log` |
| BE (C++) | исполнение фрагментов плана, хранение tablet (shared-nothing) | `storage_root_path` (сегменты, rowsets, meta RocksDB), `be.INFO` |
| CN (C++, тот же бинарник) | исполнение, кэш данных объектного хранилища (shared-data) | datacache, временные файлы |
| Object Storage / HDFS | данные shared-data, репозитории backup, EXPORT, внешние каталоги | данные таблиц, бэкапы |
| Внешние IdP | LDAP / JWT (JWKS) / OAuth2 через `SECURITY INTEGRATION` | — |
| Ranger (опц.) | внешняя авторизация (`access_control = ranger`) | политики |

## 2. Реестр сетевых интерфейсов (порты по умолчанию)

| # | Канал | Порт | Протокол | Аутентификация | Авторизация | TLS | Проверено |
|---|---|---|---|---|---|---|---|
| N1 | Клиент → FE | 9030 | MySQL | native (SHA-1 scramble) / LDAP (clear password) / JWT / OAuth2 | RBAC `Authorizer` | поддерживается при `ssl_keystore_location`; **не принудителен** (`ssl_force_secure_transport=false`); localhost освобождён | стат.+дин. |
| N2 | Клиент → FE | 8030 | HTTP REST/UI | Basic; часть эндпоинтов анонимна при `enable_http_auth=false` (по умолчанию) | частично (`checkUserOwnsAdminRole`, `require*IfHttpAuthEnabled`) | HTTPS 8443 при `enable_https=true` (выкл.) | стат.+дин. |
| N3 | Клиент → FE | `arrow_flight_port` (−1, выкл.) | Arrow Flight SQL | Basic → токен | RBAC | не исследовано | стат. |
| N4 | FE ↔ FE | 9010 | BDB JE replication | членство по helper/hosts | — | **не реализовано** (SSL-параметры BDB JE не задаются) | стат. |
| N5 | FE ↔ FE | 8030 | HTTP (meta sync, `/api/bootstrap` с cluster token) | cluster token | — | как N2 | стат. |
| N6 | BE/CN → FE | 9020 | Thrift FrontendService (91 метод) | взаимной аутентификации узлов нет; часть методов принимает user/passwd | частично | **не реализовано** (нет TSSL в FE/BE) | стат. (частично) |
| N7 | FE → BE/CN | 9060 | Thrift BackendService | нет | нет | **не реализовано** | стат. |
| N8 | FE ↔ BE ↔ BE/CN | 8060 | BRPC PInternalService / LakeService | **нет** | **нет** | опц. при BE `enable_https=true` (выкл.), только сервер, без mTLS | стат. |
| N9 | Клиент/BE → BE | 8040 | HTTP (stream load, download, update_config, greplog, pprof…) | Basic → FE `checkAuth` **только** при BE `enable_http_auth=true` (выкл.); download — cluster token | привилегия OPERATE/NODE через FE | опц. `enable_https` | стат.+дин. |
| N10 | Клиент → BE | `arrow_flight_port` (−1) | Arrow Flight (данные по ticket) | нет; ticket = query id | — | не исследовано | стат. |
| N11 | BE → BE | 8040 `/api/_tablet/_download` | HTTP clone | cluster token (`enable_token_check=true`) | путь ⊂ store paths | как N9 | стат.+дин. |
| N12 | FE → LDAP | 389/636 | LDAP | bind DN | — | `ldaps` только при `authentication_ldap_simple_ssl_conn_allow_insecure=false` (по умолчанию plain) | стат. |
| N13 | FE/BE → S3/HDFS | 443/… | SDK | ключи/IAM в storage volume / catalog / resource | — | зависит от SDK/endpoint | не исследовано |
| N14 | FE локально | UDS `groovy_debug.sock` | Groovy shell | права ФС | — | — | стат. (выкл. по умолч.) |

## 3. Доверительные границы

```
 [Клиенты/приложения]  --N1,N2,N3-->  ┌──────────── TB1: периметр кластера ────────────┐
 [Администраторы СУБД] --N1,N2------> │  FE (RBAC, аудит, конфигурация)                 │
                                      │    │ N4/N5 (FE↔FE, без TLS)                      │
                                      │    │ N6/N7/N8 (FE↔BE, без аутентификации узлов)  │
                                      │  BE/CN  ── N8/N11 (BE↔BE) ──  BE/CN             │
                                      └────┼────────────────────────────────────────────┘
                                           │ N13
                          TB2: [Object Storage / HDFS / внешние каталоги]
 [Администратор ОС] ── TB3: файловая система FE (BDB JE, логи) и BE (сегменты) ──
 [IdP LDAP/JWT/OAuth2] ── TB4: доверие к внешней идентичности (управляется привилегией SECURITY)
```

Ключевые свойства модели доверия (подтверждены кодом):
1. **Авторизация есть только на FE.** BE/CN исполняют любой корректный фрагмент плана, пришедший по BRPC/Thrift:
   контекста пользователя и проверки прав на уровне BE нет. Внутренняя сеть кластера (TB1) должна считаться
   доверенной. Узлы друг друга не аутентифицируют.
2. **Cluster token** — единственный общий секрет для FE↔FE и BE-download. По умолчанию он передаётся по каналам
   без TLS.
3. **Внешняя идентичность (TB4)** настраивается на SQL-уровне привилегией `SECURITY`. Ею по умолчанию обладают
   `db_admin` и `security_admin`. `authentication_chain` меняется привилегией `OPERATE`.
4. **Администратор ОС (TB3)** имеет полный доступ к данным: шифрования данных at rest на уровне StarRocks
   не найдено в рамках исследованного кода (`encryption/*` — ключи для shared-data/файлов, отдельно не исследовалось).

## 4. Модель субъектов (встроенные идентичности и роли)

Источник: `FE/authorization/AuthorizationMgr.java:164-289` (`initBuiltinRolesAndUsers`).
Динамическое подтверждение: `evidence/t_run.out` (`SHOW GRANTS FOR ROLE ...`).

| Субъект | Привилегии (по умолчанию, неизменяемы — `disableMutable()`) | Доступ к данным |
|---|---|---|
| user `root` | роль `root`: ALL на все типы объектов; пароль по умолчанию пустой (`AuthenticationMgr.java:114`); роль нельзя отозвать у root (`AuthorizerStmtVisitor.visitRevokeRoleStatement`); Ranger обходится (`RangerAccessController.java:162`) | полный |
| `db_admin` | ALL на TABLE/VIEW/MV/DB/CATALOG/FUNCTION/…; SYSTEM: CREATE_RESOURCE, PLUGIN, FILE, BLACKLIST, **OPERATE**, CREATE_EXTERNAL_CATALOG, REPOSITORY, CREATE_RESOURCE_GROUP, CREATE_GLOBAL_FUNCTION, CREATE_STORAGE_VOLUME, **SECURITY** | **полный** (SELECT/EXPORT на все таблицы) |
| `user_admin` | SYSTEM: **GRANT**; **IMPERSONATE ON ALL USERS** | косвенный: самовыдача прав, EXECUTE AS |
| `security_admin` | SYSTEM: **SECURITY, OPERATE** | прямого нет; косвенный через OPERATE (ADMIN EXECUTE) и IdP |
| `cluster_admin` | SYSTEM: NODE, CREATE_WAREHOUSE; ALL на WAREHOUSE | прямого нет; NODE позволяет менять состав кластера (гипотеза H-11) |
| `public` | SELECT на `information_schema.*` | метаданные в пределах прав пользователя |

## 5. Таблица Entry Point → Identity → AuthN → AuthZ → Enforcement → Resource

| Entry point | Identity | AuthN | AuthZ | Enforcement point | Resource | Пробел |
|---|---|---|---|---|---|---|
| MySQL 9030 SQL | user@host / ephemeral (IdP) | `AuthenticationHandler.authenticate` (native → `authentication_chain`) | RBAC/Ranger | `Authorizer` + `AuthorizerStmtVisitor` (analyze) | все объекты | нет |
| MySQL `ADMIN EXECUTE ON FRONTEND` | любой с OPERATE | как выше | `visitExecuteScriptStatement` → OPERATE | `ExecuteScriptExecutor.executeFrontendScript` (Groovy, `globalState` в binding) | JVM FE целиком | **F-03** |
| MySQL `EXECUTE AS` | user_admin | как выше | IMPERSONATE | `visitExecuteAsStatement` | контекст любого пользователя | **F-02** |
| HTTP FE 8030 (часть) | анонимно | нет (`enable_http_auth=false`) | нет | `RestBaseAction.needAuth()` | метаданные, метрики | **F-08** |
| HTTP FE `/api/_set_config` | root или (db_admin ∧ user_admin) | Basic | `checkUserOwnsAdminRole` | `SetConfigAction` | конфигурация FE | без аудита (**F-07**) |
| HTTP BE 8040 `update_config`, `greplog`, `pprof`, … | анонимно | нет (BE `enable_http_auth=false`) | нет | `verify_http_basic_auth` → `return nullopt` | конфигурация и журналы BE | **F-06** |
| HTTP BE download | любой с cluster token | token | путь ⊂ store paths | `DownloadAction::handle_normal` | файлы tablet | зависит от секретности токена (**F-09**) |
| BRPC 8060 | нет | нет | нет | — | исполнение фрагментов, данные tablet | **F-09** (архитектурное) |
| Thrift 9060 / 9020 | нет / частично | нет / частично | нет / частично | — | задачи BE, метаданные FE | **F-09**, H-12 (не завершено) |
