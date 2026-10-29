# hypotheses.md — гипотезы и сценарии обхода

Статусы: **Подтверждена** (→ findings), **Опровергнута**, **Открыта** (не проверена), **Частично**.

## A. Защита данных от администраторов (приоритет 1)

| ID | Модель нарушителя | Гипотеза | Точка входа / код | Статус | Комментарий |
|---|---|---|---|---|---|
| H-01 | A (db_admin) | Прямой SELECT к данным | `AuthorizationMgr.java:194-226` | **Подтверждена** → F-01 | дин. T-ADM-01 |
| H-02 | C (user_admin) | Самовыдача SELECT / роли db_admin | `AuthorizerStmtVisitor.java:1438-1522` | **Подтверждена** → F-02 | дин. T-ADM-03 |
| H-03 | C (user_admin) | IMPERSONATE / EXECUTE AS любого пользователя | `AuthorizerStmtVisitor.java:1358` | **Подтверждена** → F-02 | дин. T-ADM-04 |
| H-04 | C | Выдача себе роли `root` / `cluster_admin` | `visitGrantRoleStatement` | **Опровергнута** | «Can not grant root or cluster_admin role except root user» |
| H-05 | A, E (OPERATE) | Исполнение кода в FE через `ADMIN EXECUTE ON FRONTEND` | `ExecuteScriptExecutor.java:61-80` | **Подтверждена (стат.)** → F-03 | исполнение не выполнялось |
| H-06 | A, E | `ADMIN EXECUTE ON <BE>` даёт исполнение команд ОС | `BE/script/script.cpp:186-193,235` | **Опровергнута (стат.)** | `exec` не зарегистрирован; доступны диагностические привязки, `key_cache_info` — состав вывода не исследован (открыто: H-06a) |
| H-07 | B (root) | root можно ограничить по хосту / отключить | `AuthenticationMgr`, `UserIdentity.ROOT = root@'%'` | **Открыта** | проверить `DROP USER root`, `CREATE USER root@'host'` на стенде заказчика |
| H-08 | E (SECURITY+OPERATE) | Подключение подконтрольного IdP → эфемерные идентичности | `AuthenticationHandler`, `Config.authentication_chain` | **Частично** → F-11 | предусловия подтверждены |
| H-09 | A (PLUGIN) | `INSTALL PLUGIN` = загрузка произвольного кода в FE | `visitInstallPluginStatement`, `plugin/DynamicPluginLoader` | **Открыта** | высокий приоритет; ограничения источника плагина не исследованы |
| H-10 | A (CREATE_GLOBAL_FUNCTION) | Java UDF исполняет код на BE | `enable_udf=false` по умолч. (`Config.java:1776`) | **Частично** | закрыто по умолчанию; при `enable_udf=true` — риск |
| H-10a | A (REPOSITORY+EXPORT) | `BACKUP`/`EXPORT` во внешнее хранилище вне контроля СКБ | `visitBackupStatement`, `visitExportStatement` | **Открыта** | у db_admin все нужные привилегии; аудит фиксирует Stmt |
| H-10b | A (FILE) | `CREATE FILE` / `GetSmallFileAction` — загрузка ключей/сертификатов | `GetSmallFileAction.java` (cluster token) | **Открыта** | |
| H-10c | A (CREATE_EXTERNAL_CATALOG / RESOURCE) | вывод данных через JDBC/внешний каталог (INSERT INTO external) | коннекторы | **Открыта** | |
| H-10d | A | MV / VIEW: определитель vs вызывающий — доступ к данным через представление, созданное администратором | `ViewAnalyzer`, MV refresh context | **Открыта** | |
| H-11 | D (cluster_admin, NODE) | `ALTER SYSTEM ADD BACKEND` подконтрольного узла → получение реплик | `visitAlterSystemStatement` | **Открыта** | архитектурно следует из F-09; не проверялось |
| H-12 | F (внутренние сервисы) | Thrift FrontendService: методы без проверки пользователя, доверяющие `current_user_ident` от вызывающего | `FrontendServiceImpl.java` (91 метод, 12 с проверкой пароля) | **Открыта** | по-методный разбор не завершён |
| H-13 | — | `sys.grants_to_users/roles` доступны не-GRANT-пользователю → возможность роли auditor | `sys` db | **Открыта** | |
| H-14 | H (ОС/хранилище) | Чтение сегментов/BDB JE с диска | архитектура | **Подтверждена (архит.)** | шифрования at rest на уровне StarRocks в исследованном объёме нет |
| H-15 | I (сговор) | user_admin + security_admin: создание IdP + выдача роли группе | F-02 + F-11 | **Частично** | по отдельности подтверждено |

## B. Аутентификация и авторизация

| ID | Гипотеза | Статус | Комментарий |
|---|---|---|---|
| H-20 | Пустой пароль root по умолчанию | **Подтверждена** → F-04 | |
| H-21 | Нет политики паролей / блокировки | **Подтверждена** → F-05 | |
| H-22 | Fail-open при недоступности IdP | **Опровергнута (стат.)** | `AuthenticationHandler` при ошибке провайдера → исключение; transient-ошибки не кэшируются (`directoryUnusable`) |
| H-23 | Ranger fail-open при ошибке | **Открыта** | `result == null → AccessDeniedException` (fail-closed для check); поведение при недоступности Ranger Admin (кэш политик) не исследовано |
| H-24 | Устаревший кэш прав после REVOKE в открытой сессии | **Открыта** | `ConnectContext.currentRoleIds` устанавливается при логине; проверка привилегий читает коллекции из `AuthorizationMgr` — требуется дин. тест T-AUTHZ-02 |
| H-25 | Анонимные HTTP FE эндпоинты | **Подтверждена** → F-08 | query_detail/profile защищены (опровергнута часть гипотезы) |
| H-26 | Анонимные HTTP BE эндпоинты, изменение конфигурации | **Подтверждена** → F-06 | |
| H-27 | BE `/api/_tablet/_download` без аутентификации | **Опровергнута** | требуется cluster token (`enable_token_check=true`), путь канонизируется. Остаточный риск — секретность токена (F-09) |
| H-28 | Arrow Flight BE без аутентификации | **Подтверждена (стат.)**, по умолч. выключен | ticket = query id |
| H-29 | Перебор паролей без ограничений | **Подтверждена** | 10 неудач → вход разрешён; `RejectedCredentialCache` — только для цепочки IdP, не блокировка |

## C. TLS

| ID | Гипотеза | Статус |
|---|---|---|
| H-30 | MySQL TLS не принудителен | **Подтверждена** → F-10 |
| H-31 | TLS 1.0/1.1 принимаются | **Опровергнута на JDK 17.0.20** (зависит от `java.security`) |
| H-32 | Слабые наборы шифров в TLS 1.2 | **Частично**: CBC-SHA1 принимаются; RSA-kex, 3DES, RC4, NULL, anon — нет |
| H-33 | Межузловые каналы без TLS | **Подтверждена** → F-09 |
| H-34 | LDAP без TLS по умолчанию | **Подтверждена (стат.)** → F-11 |

## D. Аудит

| ID | Гипотеза | Статус |
|---|---|---|
| H-40 | Вход не регистрируется по умолчанию | **Подтверждена** → F-07 |
| H-41 | Выход не регистрируется никогда | **Подтверждена (стат.)** → F-07 |
| H-42 | Неуспешный вход не регистрируется по умолчанию | **Подтверждена** → F-07 |
| H-43 | Нет поля «приложение» | **Подтверждена (стат.+дин.)** → F-07 |
| H-44 | HTTP-изменения конфигурации без аудита | **Подтверждена** → F-06, F-07 |
| H-45 | Пароли попадают в аудит | **Опровергнута** для `CREATE USER ... IDENTIFIED BY` (маскируется `***`); другие операторы с секретами (`CREATE CATALOG ... PROPERTIES`, `CREATE STORAGE VOLUME`) — `SqlCredentialRedactor`, дин. не проверено |
| H-46 | Администратор может отключить/исказить аудит | **Частично**: `enable_audit_sql`, `audit_log_modules` immutable (только файл + рестарт); через F-03 — да (стат.); `UNINSTALL PLUGIN` AuditLoader — открыто |
