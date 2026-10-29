# Аудит безопасности StarRocks 4.1.7 (SHA b81ff9cc) по стандарту db_dec.docx

| Файл | Содержание |
|---|---|
| [final_report.md](final_report.md) | итоговое заключение (начинать отсюда) |
| [audit_scope.md](audit_scope.md) | версия, архитектура, границы, ограничения методики |
| [architecture.md](architecture.md) | компоненты, каналы, доверительные границы, Entry Point → Enforcement |
| [requirements_matrix.md](requirements_matrix.md) | RTM: 76 атомарных критериев 2.1–5.6 |
| [findings.md](findings.md) | карточки нарушений F-01…F-13 |
| [hypotheses.md](hypotheses.md) | гипотезы и их статус |
| [test_plan.md](test_plan.md) | harness и тест-кейсы (выполненные и для стенда заказчика) |
| [coverage.md](coverage.md) | исследованный/неисследованный код, процент покрытия, следующие шаги |
| `harness/` | SQL и shell-скрипты тестов (синтетические данные) |
| `evidence/` | сырые выводы тестов |

Исходный код StarRocks в репозиторий не включён: он получен из upstream по тегу `4.1.7`.
