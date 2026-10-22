# Agent Delegation Ledger — сценарии и test plan v0.1

Дата: 22 октября 2026. Статус: DRAFT; все тесты NOT IMPLEMENTED / NOT RUN.
Спецификация: AGENT_DELEGATION_TDPD_SPEC_v0.1.md, baseline EB-01.
Использованы TDPD и tdd-test-planner; это план, не доказательство RED/GREEN.

## Общие fixtures и наблюдения

Каждый сценарий использует изолированный synthetic case, чистый inbox и отдельный storage.
Владелец O, оркестратор A, исполнители B/C, получатель Anna и посторонний Mallory.
Документ D:v1, другая версия D:v2, другой документ X; никаких личных данных.
Clock управляется только test fixture; browser не может менять время сервера.
Принципалы аутентифицируются через разные credentials, не через редактируемое поле actor_id.
ScriptedDelegationAgent создаёт воспроизводимые proposals; не имитирует принятие владельцем.
Перед каждым сценарием задан валидный root/child, если явно не указано иное.
Для отказов проверяются UI reason, durable attempt/event, отсутствие dispatch и inbox delta=0.
Для успеха проверяются UI, receiver inbox, подпись receipt и связь с root/child/snapshot.
Каждая строка ниже задаёт начальное состояние, действие и pass/fail oracle.

## Пользовательские сценарии и трассировка

| ID / приоритет / уровень | Начальное состояние и актор | Действие / событие | Наблюдаемый результат и persistence | Rules |
|---|---|---|---|---|
| S01 P0 browser e2e | O, пустой case | Открыть страницу | Empty state, нет фиктивных grants/доставок; доступна форма | R01,R11 |
| S02 P0 browser e2e | O, D:v1 и Anna выбраны | Просмотреть и подтвердить grant | Видны hash/version/срок/1 use/делегирование; один durable root, после reload тот же ID | R01,R16 |
| S03 P0 browser e2e | O, неподтверждённая форма | Отменить | Нет root и authorizing event; inbox пуст | R01 |
| S04 P0 browser e2e | O, пустые/невалидные поля | Подтвердить; отдельно direct request | Ошибка поля/INVALID_INPUT, root не создан; неизвестные поля также отвергнуты | R01,R03 |
| S05 P0 browser e2e | Active root для A | A делегирует B; B отправляет D:v1 Anna | Один child, один inbox item, confirmed и валидная receipt; после reload сохранены | R02–R07,R10–R11,R16 |
| S06 P0 browser e2e | Root для Anna | A пытается делегировать Mallory | SCOPE_ESCALATION; child не создан, отказ сохранён, нет dispatch | R03,R15 |
| S07 P0 API integration | Root action deliver/hash D:v1/audience inbox | A меняет action, hash, audience или увеличивает expiry; параметризовано | Каждая попытка SCOPE_ESCALATION, 0 children и dispatch | R03 |
| S08 P0 API integration | Child B, redelegation=false | B выдаёт grant C | REDELEGATION_DENIED, нового grant нет | R03 |
| S09 P0 API integration | Child для B | C предъявляет grant и actor_id=B | WRONG_ACTOR, ни вызова receiver, ни новой доставки | R04,R17 |
| S10 P0 browser e2e | Child привязан к D:v1 | B предлагает D:v2/другого получателя | DOCUMENT_CHANGED/отказ scope; сохранён точный reason, inbox пуст | R04,R11 |
| S11 P0 API integration | Active root/child | Исполнить в expires_at−1ms и отдельно ровно expires_at | До границы допустимо; на границе EXPIRED; каждая ветка в свежем case | R05 |
| S12 P0 browser e2e | Root и child active | O отзывает root; затем B отправляет | REVOKED, child не работает, inbox пуст; отзыв переживает reload | R05,R09,R16 |
| S13 P0 browser e2e | Active root | Дважды нажать confirm, включая pending | Один root; кнопка pending; дубликат запроса с тем же request ID возвращает тот же root | R01,R16 |
| S14 P0 browser e2e | Подтверждённая доставка | Повторить execute | LIMIT_RESERVED_OR_USED либо тот же результат для exact same attempt; inbox count=1 | R06–R07 |
| S15 P0 API integration | Два children B/C одного root | Параллельно начать две разные attempts с барьером | Ровно одна reservation/dispatch, другая отклонена; inbox count=1 | R06 |
| S16 P0 receiver integration | Receiver уже принял attempt K | Повторить K с теми же параметрами; затем K с другими | Прежняя receipt без второй записи; изменённый payload — conflict | R07 |
| S17 P0 browser e2e | Active root; receiver сохраняет, но ответ теряется | B отправляет | UI uncertain, inbox count=1, слот занят; reload не запускает retry | R08,R16 |
| S18 P0 browser e2e | Uncertain S17 | O запускает read-only сверку | Valid matching receipt → confirmed, inbox count=1; сверка не отправляет документ | R08,R10 |
| S19 P0 API integration | Dispatch отправлен, receiver receipt нет | Timeout и сверка «не найдено» | Остаётся uncertain, слот не освобождён, новая attempt не отправляется | R08 |
| S20 P0 integration | Отзыв и reserve конкурируют | Принудительно проверить оба порядка | Отзыв первым: 0 dispatch; reserve первым: не обещаем отмену, исход tracked | R09 |
| S21 P0 integration | Store недоступен до reserve | B исполняет | STORAGE_UNAVAILABLE, receiver calls=0; ошибка видна | R16 |
| S22 P0 integration | Receiver принял, local result write падает | Рестарт приложения и восстановление | Не success без receipt, слот занят; сверка может подтвердить, повторной отправки нет | R08,R16 |
| S23 P0 browser + CLI | S05 завершён | O экспортирует, отдельный verifier с trusted fingerprints проверяет | Все подписи/связи/hash/manifest valid; архив соответствует inbox/receipt | R12–R14 |
| S24 P0 verifier integration | Копия валидного архива | Изменить получателя/document/event; отдельно убрать среднее/последнее событие без изменения manifest | INVALID_SIGNATURE/HASH/CHAIN/MANIFEST; verifier nonzero, не «valid» | R12–R13 |
| S25 P0 verifier integration | Подписанный чужими ключами архив | Вложить свой public key в пакет | UNKNOWN_KEY; ключ из пакета не становится trusted | R13 |
| S26 P0 API integration | Runtime root/child или receipt | Подмена подписи, key_id, parent/case linkage; параметризовано | Запрещено исполнение; fake receipt не даёт confirmed | R04,R10 |
| S27 P0 browser/API | Нет сессии / agent session вместо O | Читать case/inbox/export; создавать/отзывать root; CSRF mutation | 401/403, нет утечки snapshot/credentials и изменений | R17 |
| S28 P0 integration | Подтверждённая доставка/отзыв | Перезапустить app и receiver | Grants, budget, events, receipt и inbox сохраняются; повтор не создаёт доставку | R16 |
| S29 P0 integration | D содержит synthetic canary, credentials известны fixture | Happy/blocked/uncertain потоки, inspect technical logs/export | Credentials отсутствуют везде; canary только в разрешённых snapshot/inbox/export document, не logs | R15 |
| S30 P1 browser e2e | Ограничение срока формы | Выбрать 1/10 минут, 0/11 минут | Границы допустимы, выход за них rejected; child expiry≤root | R03,R05 |
| S31 P0 browser e2e | Все демонстрационные данные | Пройти UI с клавиатуры | Все действия доступны, labels/focus, причины текстом; нет color-only verdict | Surface |
| S32 P1 browser e2e | Медленный/недоступный receiver | Execute; reload | Loading → uncertain/error согласно факту dispatch; UI не зависает и не сообщает false success | R08,R10,R16 |

Тесты будут именоваться e2e/Sxx-* или integration/Sxx-*; это планируемые имена, файлов нет.
Browser сценарии используют пользовательский интерфейс и реальные локальные HTTP/storage
компоненты. Integration сценарии проверяют adversarial границы, недоступные в обычном UI.
Контроль clock/барьеров/fault injection изолирован от demo/production API.

## Матрица полноты и наиболее опасные переходы

Root создание/отмена/invalid: S01–S04,S13. Делегирование/изоляция: S05–S10,S25–S27.
Time/revocation: S11–S12,S20,S30. Shared budget/replay: S14–S16.
Uncertain/recovery/durability: S17–S22,S28,S32. Evidence: S23–S26,S29.
Surface: S01–S05,S10,S12–S14,S17–S18,S23,S31–S32.
Все R01–R17 имеют сценарии. Полнота adversarial атак не заявляется.
Особенно важно: две children не означают два бюджета; revoke не отменяет прошлое;
истёкший grant не запрещает read-only сверку уже начатого исполнения;
verifier не доказывает актуальность архива без независимого checkpoint.

## RED → GREEN порядок после одобрения архитектуры

1. Проверить Docker/browser инфраструктуру отдельно: инфраструктурная ошибка не RED.
2. Написать browser acceptance S02/S05/S06/S10/S14 и интеграционные S09/S15/S26.
   Зафиксировать failures из-за отсутствующего поведения; затем минимальный сквозной slice.
3. До выдачи разрешений реальному исполнителю добавить RED S11/S12/S16–S22/S28.
4. До демонстрации evidence добавить RED S23–S25; затем подписи/экспорт/verifier.
5. Покрыть оставшиеся P0; lint/type/security/dependency checks, container cleanup.
6. Пройти owner UAT. Нельзя объявить TDPD завершённым по одним зелёным тестам.
Live LLM, blockchain и дополнительные интеграции не вытесняют обязательные проверки.

## Демо и ручная приёмка

Демо: O создаёт root для D:v1→Anna → A делегирует B → смена получателя блокируется →
нормальная доставка confirmed → второй child не обходит лимит → export valid →
копия с подменённым событием invalid. Показывать реальные inbox/receipt, не только карточку.
Симуляция ролей обозначена на экране и в рассказе. Криптографическая подпись событий
не представляется личной электронной подписью владельца или юридической доверенностью.

| UAT | Действие владельца | Условие ручной приёмки |
|---|---|---|
| U01 | Просмотреть grant перед согласием | Понятны документ, адресат, срок и делегирование без чтения JSON |
| U02 | Выполнить успешный и запрещённый потоки | Понятно, кто действовал и почему разрешено/запрещено |
| U03 | Отозвать grant, посмотреть uncertain | UI не обещает отмену прошлого и не выдаёт неизвестный исход за успех |
| U04 | Проверить экспорт и изменённую копию | Понятны проверяемая целостность и предел доверия к оператору |
| U05 | Оценить задачу целиком | Владелец явно подтверждает, что цепочка решает исходную проблему |

Вердикт UAT: NOT RUN; дата, лицо и замечания заполняются после работающего результата.

## Решения, требующие владельца до реализации

Q1. Подтвердить browser UI + отдельный CLI verifier и proposed code directory.
Q2. Подтвердить synthetic deliver_document как действие первого MVP, вместо acceptance политики.
Q3. Подтвердить предложенные ADR: Python/SQLite, Ed25519, scripted agents, одна глубина.
Q4. Принять консервативный uncertain: слот занят до сверки, автоматического retry нет;
отзыв после reservation не гарантирует отмену уже начавшегося dispatch.

Это конкретные решения для Input/Surface gate, а не повторное согласование всей идеи.
Текущее поручение — подготовка спеки и сценариев; реализация и исполняемые RED-тесты
ещё не запрошены. Правила раннего конкурсного кода остаются отдельной неопределённостью.
