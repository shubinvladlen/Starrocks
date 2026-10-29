# coverage.md — покрытие исследования

Процент покрытия показывает долю атомарных критериев, по которым есть доказательный статус.
Это **не** процент безопасности продукта.

## 1. Исследованный код (SHA `b81ff9cc`)

| Область | Файлы | Глубина | Статус |
|---|---|---|---|
| Встроенные роли/пользователи | `authorization/AuthorizationMgr.java`, `PrivilegeBuiltinConstants.java` | полностью (init) | ✅ |
| Проверка привилегий по операторам | `sql/analyzer/AuthorizerStmtVisitor.java` — 142 visit-метода сопоставлены с привилегиями (`evidence/stmt_privs.txt`) | карта; детально — GRANT/ROLE/EXECUTE AS/SCRIPT | ✅ частично |
| Аутентификация | `authentication/AuthenticationHandler.java`, `AuthenticationMgr.java`, `PlainPasswordAuthenticationProvider.java`, `LDAPAuthProvider.java` (TLS), `SslUtils.java`, `mysql/MysqlPassword.java`, `UserAuthOptionAnalyzer.java`, грамматика CREATE/ALTER USER | основной поток | ✅ |
| JWT / OAuth2 / OIDC провайдеры | `JWTAuthenticationProvider`, `OAuth2*`, `OpenIdConnectVerifier` | не исследованы | ❌ |
| Ranger | `RangerAccessController.hasPermission` | только root-bypass и fail-closed check | ⚠️ |
| MySQL TLS | `mysql/ssl/SSLContextLoader.java`, `MysqlProto.negotiate` | полностью | ✅ |
| FE HTTP | `BaseAction`, `RestBaseAction`, все `needAuth()==false`/`enable_http_auth`, `SetConfigAction`, `GetSmallFileAction`, `BootstrapFinishAction` | эндпоинты без аутентификации | ✅; остальные ~100 actions — только через базовый класс |
| Служебные операторы | `qe/ExecuteScriptExecutor.java`, `BE/script/script.cpp` | полностью | ✅ |
| Аудит FE | `plugin/AuditEvent.java`, `qe/AuditLogBuilder.java`, `qe/ConnectProcessor.auditAfterExec/formatStmt`, `common/util/LogUtil.java`, `mysql/nio/AcceptListener.java` | основной поток | ✅ |
| Конфигурация | `common/Config.java` (security-релевантные), `BE/common/config.h` | выборочно | ✅ |
| BE BRPC | `service/service_be/starrocks_be.cpp` (сервер, SSL) | без разбора методов `PInternalService` | ⚠️ |
| BE HTTP | `http/ev_http_server.cpp`, `service/service_be/http_service.cpp`, `http_auth_response.cpp`, `download_action.cpp`, флаги `need_auth/required_privilege` всех actions | ✅ |
| Arrow Flight | `arrow_flight_sql_service.cpp` (BE) | старт сервера | ⚠️ |
| Thrift FrontendService | `service/FrontendServiceImpl.java` | только подсчёт методов/проверок | ❌ |
| BDB JE / HA | `journal/bdbje` — только поиск SSL | ⚠️ |
| Коннекторы внешних каталогов | `connector/*` | не исследованы | ❌ |
| Плагины, UDF | `plugin/*Loader`, `java-extensions` | не исследованы (кроме флага `enable_udf`) | ❌ |
| Backup/Export/Repository | `backup/*`, `load/Export*` | только привилегии в visitor | ⚠️ |
| MV/View контекст исполнения | `mv/*`, `ViewAnalyzer` | не исследованы | ❌ |
| Shared-data (StarOS, LakeService, storage volume, datacache) | — | только наличие сервиса BRPC | ❌ |
| Шифрование at rest | `encryption/*`, `BE KeyCache` | не исследовано | ❌ |
| Поставка/SCA | `trivy.yaml`, `thirdparty` | не исследовано | ❌ |

## 2. Динамическая проверка

Выполнена на `allin1-ubuntu:4.1.7` (shared-nothing): выполнены тесты по умолчанию и hardened-профиль с
перезапуском узлов (T-TLS-04, T-HTTP-04, T-AUD-04, T-ADM-05 — меры §11.2 подтверждены) и роль «DBA без данных»
(T-ADM-09, 12 путей). Не выполнены на целевой конфигурации: T-TLS-05 (межузловой трафик), T-AUTHZ-02
(устаревание прав в сессии). Shared-data не проверялась.

## 3. Покрытие атомарных критериев RTM (76)

| Категория | Кол-во | Доля |
|---|---|---|
| Доказательный статус (С, СУ, НС, НП) | 54 | 71 % |
| Не подтверждено (НПд) | 6 | 8 % |
| Требует эксплуатационной проверки / нормативный документ отсутствует (ЭП) | 16 | 21 % |

Критерии со статусом ЭП нельзя закрыть по исходному коду: это процессы, состав ОС и документы /4/–/12/.

## 4. Пропуски и необходимые следующие проверки (по приоритету)

1. H-09 `INSTALL PLUGIN` (источник, подпись, исполнение в FE) — для привилегии PLUGIN у db_admin.
2. H-10a/H-10c/H-10d: BACKUP/EXPORT, внешние каталоги, контекст VIEW/MV — для валидации роли «DBA без данных» (T-ADM-09).
3. H-12: по-методный аудит `FrontendServiceImpl` (какие методы доверяют идентичности, переданной вызывающим узлом).
4. H-24: устаревание прав в открытой сессии (T-AUTHZ-02).
5. JWT/OAuth2/OIDC: проверка подписи, `aud/iss/exp`, JWKS-кэш, поведение при недоступности IdP.
6. Shared-data: доступ CN к объектному хранилищу, ключи в storage volume, видимость секретов в `DESC STORAGE VOLUME`/`SHOW CREATE CATALOG`.
7. T-TLS-04/05, T-HTTP-04, T-AUD-04 — подтверждение мер на целевой конфигурации.
8. SCA зависимостей (`trivy fs`), сравнение `4.1.7` с `branch-4.1` HEAD.
