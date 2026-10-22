# Agent Delegation Ledger — TDPD specification v0.1

Дата: 22 октября 2026, Europe/Lisbon. Статус: DRAFT FOR OWNER REVIEW.
Метод: TDPD / Test-Driven Product Development, оригинальный метод Иннокентия Бодрова.
Режим работы: Plan. Этот документ не разрешает реализацию, внешние операции или подачу.

## 1. Проблема и проверяемая ценность

BP-01. Владелец поручает задачу оркестратору, который привлекает исполнителя.
Владельцу нужно ограничить полномочия каждого участника и впоследствии проверить,
кто разрешил конкретное действие, кто его выполнил и какой результат подтвердил сервис.
Общая сессия пользователя и строка «успешно» не дают такой проверяемой цепочки.

Успех MVP: владелец создаёт разрешение, видит дочернее разрешение и одну подтверждённую
доставку; попытки расширения прав, подмены и повтора не создают доставок; выгруженный
пакет проходит отдельную проверку. Понимание и полезность проверяются владельцем на UAT.
Ожидаемые результаты синтетического набора: 1 допустимая доставка, 0 недопустимых,
0 автоматических повторов при неопределённом исходе. Это критерии, не измеренные результаты.

## 2. Источники и область решений

Базовая версия evidence baseline: EB-01, 2026-10-22.

| Источник | Авторитет / доступ / статус | Применение |
|---|---|---|
| Решения владельца в этом чате, 21–22 октября | Первичный, частный; концепция согласована | Делегирование, журнал, без блокчейна |
| AGENTS.md и START-HERE.md корня Hackathons | Обязательный локальный контракт | Docker, изоляция, запрет самовольных внешних действий |
| Предыдущие readiness/runbook в этой папке | Исторический, частный; датирован 14 октября | История, не актуальная спецификация продукта |
| Portfolio Code Quality + TDPD Standard v1.0 и Code Quality Defaults v1.1 | Сохранённые документы от 25 сентября | Контракт качества; команды адаптировать к Tower |
| RFC 8693, https://www.rfc-editor.org/rfc/rfc8693.html | Публичный стандарт; исследован в чате 21 октября | Термины delegation/actor, не заявление совместимости |
| RFC 9396, https://www.rfc-editor.org/rfc/rfc9396.html | Публичный стандарт; исследован в чате 21 октября | Детализация разрешений, не обязательная OAuth-интеграция |

Владелец уточнил: «PDF» означало TDPD; отдельного PDF-источника нет.
Конфликт разрешён: прежний Agent Permission Firewall с тремя инструментами заменён
одним рабочим процессом делегирования доставки документа. Исторические файлы не изменять.
Изменение действия, глубины делегирования или доверенной стороны требует новой версии
спеки и пересмотра затронутых сценариев до RED/реализации.
Условия конкурса и допуск prebuilt-кода эта спека не устанавливает.

## 3. MVP и исключения

Действие: deliver_document в локальный synthetic inbox.
Цепочка: владелец → оркестратор → исполнитель; третий уровень запрещён.
Два экземпляра исполнителя используются для проверки общего лимита.
Никаких реальных договоров, персональных данных, юридических подписей, платежей,
публичной публикации, live LLM, OAuth, MCP или блокчейна в обязательном MVP.
ScriptedDelegationAgent — явно обозначенный детерминированный адаптер ролей.
Он не доказывает качество или доступность настоящей модели.

## 4. Предложенный Surface contract — требует подтверждения

Основной интерфейс: локальная веб-страница, три области:
«Разрешение», «Цепочка событий», «Тестовый ящик».
Поток: выбрать документ/получателя → просмотреть ограничения → подтвердить →
делегировать → выполнить или показать отказ → экспортировать доказательства.
Вторичный интерфейс: независимая проверка экспортированного пакета через CLI.
CLI не заменяет браузерные acceptance tests основного потока.

Экраны/состояния: пустой список; просмотр документа; форма; pending;
active/revoked/expired; blocked с причиной; dispatching; confirmed; uncertain;
ошибка хранилища/сервиса; результат проверки пакета; состояние после перезагрузки.
Повторное нажатие не создаёт второй grant или dispatch. При pending кнопка отключена.
Отмена формы не создаёт разрешение. Обновление страницы восстанавливает сохранённое состояние.
Не разрешать форму при пустом документе/получателе или недопустимом сроке.
Предложение: срок 1–10 минут, по умолчанию 5; valid при now < expires_at, иначе expired.
Цель UX: desktop 1280×800, без горизонтальной прокрутки на 768 px; клавиатура,
видимые focus/labels, причины отказа не только цветом. Полировка — manual UAT.

Предложенная будущая граница кода: work/agent-delegation-ledger/ в этом workspace.
Этот каталог и приложение пока не созданы. Не переиспользовать чужие runtime или данные.
Стек-предложение: Python + SQLite + server-rendered HTML; криптография Ed25519
через проверенную библиотеку, не собственная реализация; Playwright для browser e2e.
Команды build/run/test/scan/health/logs/stop должны появиться в README после ревью
Dockerfile/Compose. Сейчас проверенных команд проекта нет; не заявлять Docker-readiness.

## 5. Модель доверия и канонические данные

Канонический durable aggregate: DelegationCase, идентификатор case_id.
Содержит snapshot документа, root grant, child grants, attempts и receipts.
Журнал, UI и экспорт — проекции этого aggregate, не отдельные источники истины.
Импортеров, фоновых синхронизаторов, загрузки пакета обратно в runtime и scheduler нет.
Все изменения проходят через авторизационный сервис/исполнитель; export только read-only.

Владелец аутентифицирован отдельной локальной demo-сессией; это не проверка личности.
Оркестратор и исполнители имеют разные credentials. Principal определяется по
проверенным credentials, а не actor_id из JSON/аргумента модели.
Доверенные компоненты: authorization service, dispatcher, их storage и provisioning ключей.
Недоверенные: предложения агентов, документы, HTTP inputs, экспорт при проверке.
Компрометация владельца хоста или всех доверенных ключей вне защиты MVP.

| Entity | Обязательные поля |
|---|---|
| DocumentSnapshot | document_id, version_id, bytes, SHA-256, immutable=true |
| RootGrant | grant_id, case_id, owner_id, orchestrator_id, action, snapshot_hash, recipient_id, audience, issued_at, expires_at, max_uses=1, delegation_allowed=true |
| ChildGrant | grant_id, parent_id, authenticated_issuer, executor_id, action, snapshot_hash, recipient_id, audience, issued_at, expires_at, max_uses=1, delegation_allowed=false |
| Attempt | attempt_id, case_id, root_id, child_id, authenticated_actor, actual_action_digest, idempotency_key, decision, reason, execution_status |
| Receipt | receipt_id, attempt_id, root_id, child_id, receiver_id, snapshot_hash, recipient_id, received_at, signature |
| EvidenceEvent | event_id, case_id, sequence, previous_hash, kind, actor_id, server_time, payload_digest, payload, signer_key_id, signature |

Root authorization подписывает authorization service после подтверждения владельцем;
это свидетельство сервиса, не личная криптографическая подпись владельца.
Оркестратор подписывает child grant; receiver подписывает receipt; ledger подписывает
события. Разные роли используют разные ключи. Ключи не в исходниках, образе или экспорте.
Provisioning связывает key_id и роль вне импортируемого пакета.

## 6. Детерминированные правила

R-01. Только владелец создаёт/отзывает root grant после просмотра точного snapshot,
получателя, действия, срока и права делегирования. Снимок хранится неизменно.
R-02. Только указанный оркестратор делегирует; child создаётся только под active root.
R-03. Child должен точно сохранять action, hash, recipient, audience; срок не длиннее root;
исполнитель задан явно, дальнейшее делегирование false. Неизвестные поля/типы отклоняются.
R-04. Исполнять может только аутентифицированный executor child grant; проверяются обе
подписи, trusted keys, связи parent/case и совпадение фактических параметров.
R-05. Grant valid: не отозван, now < expires_at. Проверка повторяется при резервировании
доставки. Время сервера; тестовый clock доступен только в test environment.
R-06. Одна root grant допускает не более одного dispatch независимо от числа children.
Атомарное резервирование общего слота предшествует обращению к receiver.
R-07. Один attempt имеет стабильный idempotency_key. Receiver сохраняет не более одного
сообщения на этот ключ, возвращает прежнюю receipt для совпадающего повтора;
тот же ключ с другими параметрами даёт conflict без новой записи.
R-08. После отправки с неизвестным результатом слот не освобождается и автоматического
повтора нет. Разрешена read-only сверка receiver по ключу; до достоверной receipt — uncertain.
Отсутствие receipt не доказывает отсутствие доставки. Новый root автоматически не создаётся.
R-09. Отзыв и резервирование сериализованы: отзыв раньше резервирования блокирует dispatch;
если dispatch уже зарезервирован, UI предупреждает, что отзыв не гарантирует отмену.
Существующая подтверждённая доставка никогда не исчезает из-за отзыва.
R-10. Успех показывается только по валидной receiver receipt, связанной с фактическим
документом/получателем/attempt. HTTP 200 без проверяемой receipt не является confirmed.
R-11. Для подтверждённого результата UI показывает фактическую запись inbox и receipt.
Blocked означает 0 вызовов receiver для этой попытки и 0 новых сообщений.
R-12. Ledger append-only через API, упорядочен по case sequence; подпись покрывает весь
канонический event и previous_hash. Proposal: RFC 8785 JSON canonicalization + Ed25519.
Любое изменение signed payload или разрыв связей даёт verification failure.
R-13. Export содержит snapshot, grants, events, receipts, schema version и подписанный
manifest с count и final_hash. Верификатор требует trusted key fingerprints извне;
ключ, вложенный самим пакетом, не создаёт доверия.
R-14. Verification означает целостность относительно доверенных ключей/manifest.
Это не доказательство прочтения человеком, истинности всех утверждений или полноты
истории до независимого checkpoint. Полная перепись доверенным оператором вне гарантии.
R-15. Запрещённые действия тоже сохраняются как события с причиной, без credentials.
Подробные synthetic документы только в snapshot/inbox; не дублировать их в технических logs.
R-16. Невозможность сохранить pre-dispatch authorization/attempt блокирует отправку.
Сбой сохранения результата после dispatch оставляет uncertain/recovery-needed, не success.
Перезапуск не сбрасывает использованный слот, отзыв, attempts или inbox.
R-17. Все защищённые read/write/export endpoints проверяют demo-session/role;
нет публичных inbox/export, wildcard CORS или actor override. Owner mutations защищены от CSRF.

Причины отказа: INVALID_INPUT, UNAUTHENTICATED, WRONG_ACTOR, WRONG_AUDIENCE,
INVALID_SIGNATURE, UNKNOWN_KEY, SCOPE_ESCALATION, REDELEGATION_DENIED,
DOCUMENT_CHANGED, REVOKED, EXPIRED, LIMIT_RESERVED_OR_USED, STORAGE_UNAVAILABLE.
При нескольких дефектах приоритет: parse/auth → signatures/chain → scope →
revoked/expired → atomic limit. Ни один отказ не создаёт dispatch.

## 7. Lifecycle и границы состояний

Root: active → revoked; expired вычисляется по времени; reserved/used — независимый
статус общего слота, не замена validity. Истёкший grant остаётся в истории.
Attempt: blocked либо reserved → dispatching → confirmed | uncertain.
Падение после reservation до подтверждения результата восстанавливается как uncertain;
консервативный false block допустим, автоматическое повторное исполнение — нет.
Сверка переводит uncertain → confirmed только по достоверной receipt.
Неизвестный исход не переводится автоматически в available.

## 8. Архитектурные решения для Input gate

ADR-01 proposed: локальный browser UI, authorization/ledger/dispatcher и отдельный
synthetic receiver; логически разные роли и credentials, допускается один demo-host.
ADR-02 proposed: SQLite durable state, транзакционное резервирование root budget,
receiver idempotency unique constraint; отдельные хранилища приложения и receiver.
ADR-03 proposed: Ed25519 + canonical JSON; trusted key fingerprints задаются отдельно.
ADR-04 proposed: ScriptedDelegationAgent, без live provider. Никакого заявления о полном
соответствии OAuth, криптографической личной подписи или юридической доверенности.
ADR-05 required: Tower Docker amd64, non-root, loopback, resource/PID/log limits,
capability restrictions, browser sandbox, без privileged/host network/socket mounts.
Temporary tests --rm, отдельные synthetic volumes; никаких down -v/prune.
ADR-06 proposed: сбои после reservation всегда fail-closed/uncertain; безопасность
предпочтительнее доступности в этом MVP. Требует осознанной приёмки UX владельцем.

## 9. Reliance / harm preflight

В MVP все данные synthetic, действия локальные, отказаться от демо легко; внешних
обязательств нет. Главный риск — ошибочно принять демонстрацию за юридическое доказательство
или production-ready авторизацию. UI явно показывает DEMO и границу гарантий.
Для реальных документов/согласий нужны отдельный review идентификации, основания полномочий,
условий принимающего сервиса, защиты ключей, хранения, recovery и правовых требований.
Такое расширение требует нового owner decision, не входит в это разрешение на планирование.

## 10. Связанные артефакты и gates

Сценарии, test matrix, UAT и порядок реализации: AGENT_DELEGATION_SCENARIOS_v0.1.md.
Input: APPROVED (ADR-01..ADR-06, модель данных и 17 правил утверждены в docs/ARCHITECTURE_CONTRACT.md).
Surface: APPROVED (3-панельный browser UI + автономный CLI verifier утверждены).
Evidence: EB-01 зафиксирован; стек Python 3.12/FastAPI/SQLite/Ed25519 выбран.
Reliance/harm: synthetic-only классификация описана, production вне scope.
RED: READY TO START. Сценарии S01–S32 готовы к кодированию тестов.
GREEN: NOT STARTED. Код и тестовые результаты отсутствуют.
Output/UAT: NOT STARTED. Утверждение спеки не означает приёмку продукта.
