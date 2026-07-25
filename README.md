# Задача: золотое решение для php-standard-library/php-standard-library PR #740

> Это оценочная задача (evaluation task) для кодящего ИИ-агента. Вы **не просто реализуете фичу** —
> вы проектируете качественную задачу, которая проверяет, способен ли ИИ воспроизвести это
> изменение, имея на входе только постановку задачи и базовый репозиторий.

---

## 1. Что улучшаем

**Исходный PR:** <https://github.com/php-standard-library/php-standard-library/pull/740>
**Заголовок:** `feat(io): add composable handle decorators (Concat, Joined, Tee, Truncated, Bounded, FixedLength, Iterable, Sink) and replace internal duplicates`

- **Язык:** PHP 8.4 (Composer, PHPUnit)
- **Где правка:** пакет `packages/io` (новые компонуемые декораторы handle-ов в неймспейсе `Psl\IO`); плюс рефакторинг в `packages/http-client` и `packages/message`, где самописные внутренние handle-классы заменяются на новые переиспользуемые декораторы.
- **Суть:** в `Psl\IO` появляется набор **компонуемых декораторов** над `ReadHandleInterface` / `WriteHandleInterface` / `ReadWriteHandleInterface`: `ConcatReadHandle` (последовательное чтение нескольких handle-ов как одного), `FixedLengthReadHandle` (чтение ровно N байт), `BoundedReadHandle` (ограничение общего числа прочитанных байт), `TruncatedReadHandle` (усечение до максимальной длины), `TeeWriteHandle` (запись в два handle-а одновременно), `JoinedReadWriteHandle` (склейка read- и write-handle в один read-write), `Sink{Read,ReadWrite,Write}Handle` (sink-обёртки). Эти декораторы заменяют дублирующиеся ad-hoc реализации, ранее жившие в `http-client` (H1/H2 body-handles, `LimitedReadHandle`) и `message` (`ConcatenatedReadHandle`), консолидируя логику композиции потоков в одном месте.

Файлы, затронутые исходным PR (для ориентира — что изучать и откуда брать кандидатов в тесты):

| Production-код | Тесты |
| --- | --- |
| `packages/io/src/Psl/IO/ConcatReadHandle.php`, `FixedLengthReadHandle.php`, `BoundedReadHandle.php`, `TruncatedReadHandle.php`, `TeeWriteHandle.php`, `JoinedReadWriteHandle.php`, `SinkReadHandle.php`, `SinkReadWriteHandle.php`, `SinkWriteHandle.php` (новые) | `packages/io/tests/unit/ConcatReadHandleTest.php`, `FixedLengthReadHandleTest.php`, `BoundedReadHandleTest.php`, `TruncatedReadHandleTest.php`, `TeeWriteHandleTest.php`, `JoinedReadWriteHandleTest.php`, `SinkReadHandleTest.php`, `SinkReadWriteHandleTest.php`, `SinkWriteHandleTest.php` (новые) |
| `packages/io/src/Psl/IO/IterableReadHandle.php`, `MemoryHandle.php` (изменены) | `packages/io/tests/fixture/NonCloseableWriteHandle.php`, `SlowWriteHandle.php` (новые фикстуры) |
| `packages/http-client/src/Psl/HTTP/Client/Internal/{H1/FixedLengthBodyHandle,H1/ResponseReader,H2/ResponseBodyHandle,LimitedReadHandle}.php`, `Exception/ProtocolException.php` (рефакторинг на новые декораторы) | `packages/http-client/tests/unit/Internal/{H1/FixedLengthBodyHandle,H1/MisbehavingServer,H1/ResponseReader,LimitedReadHandle}Test.php` |
| `packages/message/src/Psl/Message/Internal/ConcatenatedReadHandle.php`, `serialize.php` (рефакторинг) | (покрываются существующими тестами `packages/message/tests/unit/`) |

> Примечание: исходный PR влит не в `main`, а в ветку разработки `next`. Для вашей задачи отправной точкой служит снапшот в `base/` (= `base_commit`, состояние непосредственно перед PR #740), а изменения PR — это «existing solution» (см. раздел 4).
>
> ⚠️ PR крупный и многопакетный. Ядро изменения — **декораторы в `packages/io`**. Допустимо (и рекомендуется) ограничить постановку самодостаточным, тестируемым подмножеством — например, набором io-декораторов и их unit-тестами, — сохранив все P2P зелёными. Главное — постановка должна быть полной для выбранного объёма (см. раздел 3).

---

## 2. Что вам дано

- **[`base/`](base/)** — снапшот репозитория php-standard-library на коммите **непосредственно перед** вливанием PR #740 (исходное состояние, `base_commit`). Полное дерево: `packages/*/src` и `packages/*/tests`, `config/` (в т. ч. `config/phpunit.xml.dist`), `docs/`, `examples/`, `composer.json`/`composer.lock`. История веток/коммитов не задана — вы выстраиваете её сами (см. раздел 4).
- **[`base/.agen-runtime/`](base/.agen-runtime/)** — детерминированное окружение для сборки и прогона тестов:
  - [`Dockerfile.agen-runtime`](base/.agen-runtime/Dockerfile.agen-runtime) — образ на `php:8.4-cli` (расширения `bcmath`, `intl`, `zip`, `brotli`, `sodium`; Composer); ставит зависимости (`composer install`) и гоняет `phpunit -c config/phpunit.xml.dist`;
  - [`run-tests-eval.sh`](base/.agen-runtime/run-tests-eval.sh) — скрипт: парсит команду тестов из Dockerfile, умеет гонять весь набор или точечный список файлов (для PHPUnit запускает `./vendor/bin/phpunit <файлы>`);
  - [`metadata.json`](base/.agen-runtime/metadata.json) — шаблон метаданных задачи (сейчас заполнен заглушками `agen-core`, его нужно заполнить).

---

## 3. Что нужно сдать (deliverables)

В папке этой задачи (`00_tasks/task_04_php-standard-library__php-standard-library__740/`) по итогу должно быть:

1. **Золотое решение (golden solution)** — чистая, независимая реализация того же изменения в ветке `golden-solution` с правильной структурой коммитов (см. раздел 4). Не копировать исходный PR дословно; качество — не ниже оригинала.
2. **F2P-тесты** (Fail-to-Pass) — падают на base-коммите (нужная функциональность отсутствует), проходят после `[sol]`.
3. **P2P-тесты** (Pass-to-Pass) — существующие тесты, не затронутые правкой; проходят и до, и после.
4. **`PROBLEM_STATEMENT.md`** — постановка задачи для агента. Что в нём должно быть — см. раздел 10.
5. **`PR_DESCRIPTION.md`** — описание PR золотого решения. Что в нём должно быть — см. раздел 10.
6. **Заполненный** [`base/.agen-runtime/metadata.json`](base/.agen-runtime/metadata.json) (см. раздел 6).
7. **`metadata.csv`** — итоговая строка задачи в табличном формате датасета (см. раздел 7).

> ⚠️ **Главный критерий приёмки — задачу решает агент, а не вы.**
>
> Во время оценки агент получает **только** `problem_statement` + базовый репозиторий (`base/`). Он **не видит** ваше решение, ваши тесты и исходный PR. Качество задачи оценивается по тому, способен ли **сам агент** на этом входе:
> - реализовать изменение;
> - пройти **все** F2P-тесты;
> - сохранить **все** P2P-тесты.
>
> **Если агент не может решить задачу из `problem_statement` + `base` и провести тесты — решение НЕ засчитывается.** Поэтому постановка должна быть самодостаточной, однозначной и полной: всё необходимое для решения следует из неё, без опоры на исходный PR или ваши пояснения.

---

## 4. Процесс

### 4.1. Изучите контекст
Прочитайте исходный PR #740 и связанные обсуждения, разберитесь в неймспейсе `Psl\IO`: интерфейсы `ReadHandleInterface` / `WriteHandleInterface` / `ReadWriteHandleInterface`, существующие handle-классы и трейты (`ReadHandleConvenienceMethodsTrait`, `WriteHandleConvenienceMethodsTrait`), семантика `read`/`write`/`close`/`tryRead`. Посмотрите, как сейчас устроены самописные handle-обёртки в `http-client` и `message`, которые PR консолидирует.

### 4.2. Ветки и базовый коммит
В `base/` зафиксируйте исходный снапшот как базовый коммит, заведите ветку решения:

```bash
git checkout <default-branch>      # ветка по умолчанию
git pull
git checkout -b golden-solution
```

Внесите изменения исходного PR как отправную точку (ваш «existing solution») — чтобы видеть полный diff оригинала:

```bash
git checkout existing-solution -- .
```

### 4.3. Улучшите решение
Берите оригинал за основу, но:
- сохраните корректную логику и работающие части;
- улучшите читаемость и структуру;
- рефакторите там, где уместно;
- надёжнее обрабатывайте граничные случаи (пустые handle-ы, чтение за границей, частичные write, закрытие/двойное закрытие, нулевая длина).

### 4.4. Коммит только с кодом
Первый коммит — **только реализация**, без тестов:

```bash
git commit -am "[sol]: <краткое описание изменения>"
```

### 4.5. Добавьте тесты и метаданные
Отдельными коммитами — F2P/P2P-тесты и метаданные.

---

## 5. Структура коммитов и PR

Все коммиты — в ветке `golden-solution`, строго в этом порядке и с префиксами:

| Коммит | Что содержит |
| --- | --- |
| `base` | снапшот php-standard-library на коммите перед PR #740 |
| `[sol]` | изолированный код решения (без тестов и лишних изменений) |
| `[f2p]` | тесты, падающие на base и проходящие после `[sol]` |
| `[meta]` | `metadata.json` (problem_statement, hints, маппинг тестов) |

**Требования к PR:**
- **Заголовок:** `[GOLDEN SOLUTION] Add composable IO handle decorators`
- **Описание** оформляется в `PR_DESCRIPTION.md` и должно включать:
  1. **Problem** — чего не хватало / что дублировалось на base;
  2. **Approach** — как работает ваше решение и чем оно лучше оригинального PR;
  3. **Testing Strategy** — какое поведение проверяется и какие граничные случаи покрыты.

---

## 6. metadata.json — поля для заполнения

Заполните [`base/.agen-runtime/metadata.json`](base/.agen-runtime/metadata.json), заменив заглушки `agen-core` на реальные значения.

| Поле | Значение для этой задачи |
| --- | --- |
| `instance_id` | идентификатор задачи (напр. `php-standard-library__php-standard-library__740`) |
| `task_title` | краткий заголовок задачи |
| `problem_statement` | текст постановки (тот же, что в `PROBLEM_STATEMENT.md`) |
| `problem_statement_variant` | усложнённый вариант промпта (как его дал бы нетехнический человек) |
| `hints` | подсказки: ключевые файлы/места кода |
| `repo` | `php-standard-library` |
| `repo_path_or_url` | URL предоставленного репозитория |
| `FAIL_TO_PASS` | JSON-массив путей к F2P-тестам от корня репозитория |
| `PASS_TO_PASS` | JSON-массив путей к P2P-тестам |
| `language` | `PHP` |
| `docker_file` | `.agen-runtime/Dockerfile.agen-runtime` |
| `run_script` | `.agen-runtime/run-tests-eval.sh` |
| `task_type` | напр. `feature` |
| `task_category` | напр. `io` / `refactor` |
| `repo_category` | напр. `standard-library` |
| `version` | `1` |
| `container_mem` / `container_memswap` | напр. `4g` / `4g` |
| `container_network_needed` | `FALSE` для io-декораторов (тесты на in-memory handle-ах); проверьте, если включаете http-client |

---

## 7. metadata.csv — итоговая строка датасета

Помимо `metadata.json`, задача сдаётся **одной строкой** в общем табличном датасете (`metadata.csv`): шапка со столбцами + одна строка данных по этой задаче.

Отличия от `metadata.json`:
- столбцы `docker_file` и `run_script` содержат **полное содержимое** файлов (а не пути): целиком текст `.agen-runtime/Dockerfile.agen-runtime` и `.agen-runtime/run-tests-eval.sh`;
- добавлены SHA коммитов (`base_commit`, `golden_commit`, `test_commit`), поля доступа/лицензии и команда сброса репозитория.

**Правила CSV-экранирования:** поле, содержащее запятую, перевод строки или двойную кавычку, заключается в двойные кавычки `"…"`; внутренние двойные кавычки удваиваются (`""`). Поэтому JSON-массивы в `fail_to_pass`/`pass_to_pass` и многострочные `docker_file`/`run_script` всегда идут в кавычках.

| Столбец | Что писать | Кто заполняет |
| --- | --- | --- |
| `instance_id` | уникальный ID задачи (UUID или `php-standard-library__php-standard-library__740`) | кандидат |
| `problem_statement` | тот же текст, что в `PROBLEM_STATEMENT.md` | кандидат |
| `problem_statement_variant` | усложнённый вариант промпта | кандидат |
| `hints` | подсказки (ключевые файлы/места кода) | кандидат |
| `repo` | `php-standard-library` | кандидат |
| `repo_access` | `public` | кандидат |
| `license` | `MIT` | кандидат |
| `repo_path_or_url` | URL предоставленного репозитория | кандидат |
| `fail_to_pass` | JSON-массив путей к F2P-тестам | кандидат |
| `pass_to_pass` | JSON-массив путей к P2P-тестам | кандидат |
| `language` | `PHP` | кандидат |
| `docker_image_url` | URL собранного docker-образа (если выдаётся пайплайном) | пайплайн / оставить пустым |
| `docker_file` | **полное содержимое** `.agen-runtime/Dockerfile.agen-runtime` | кандидат |
| `base_commit` | SHA базового коммита (состояние перед PR) | кандидат |
| `golden_commit` | SHA коммита `[sol]` | кандидат |
| `test_commit` | SHA коммита `[f2p]` | кандидат |
| `run_script` | **полное содержимое** `.agen-runtime/run-tests-eval.sh` | кандидат |
| `task_category` | напр. `feature` | кандидат |
| `repo_category` | напр. `standard-library` | кандидат |
| `before_repo_set_cmd` | `git reset --hard <base_commit>` | кандидат |
| `version` | `1` | кандидат |
| `container_mem` / `container_memswap` | `4g` / `4g` | кандидат |
| `container_network_needed` | `FALSE` / `TRUE` | кандидат |
| `scenario` | `standard` / `hints` | система оценки |
| `sonnet_successes`, `sonnet_avg_toolcalls`, `sonnet_avg_loc_changed`, `sonnet_avg_files_changed`, `sonnet_avg_num_turns` | метрики прогона модели | система оценки (оставить пустыми) |
| `gemini_successes`, `gemini_avg_toolcalls`, `gemini_avg_loc_changed`, `gemini_avg_files_changed`, `gemini_avg_num_turns` | метрики прогона модели | система оценки (оставить пустыми) |

**Строка-шапка** (порядок столбцов фиксирован):

```csv
instance_id,problem_statement,problem_statement_variant,hints,repo,repo_access,license,repo_path_or_url,fail_to_pass,pass_to_pass,language,docker_image_url,docker_file,base_commit,golden_commit,test_commit,run_script,task_category,repo_category,before_repo_set_cmd,version,container_mem,container_memswap,container_network_needed,scenario,sonnet_successes,sonnet_avg_toolcalls,sonnet_avg_loc_changed,sonnet_avg_files_changed,sonnet_avg_num_turns,gemini_successes,gemini_avg_toolcalls,gemini_avg_loc_changed,gemini_avg_files_changed,gemini_avg_num_turns
```

**Схема строки данных** (значения-плейсхолдеры; поля `<…>` заполняете сами, большие поля показаны схематично):

```csv
php-standard-library__php-standard-library__740,"<problem_statement>","<problem_statement_variant>","<hints>",php-standard-library,public,MIT,<repo_url>,"[""packages/io/tests/unit/<...>Test.php""]","[""packages/io/tests/unit/<...>Test.php""]",PHP,,"<полное содержимое Dockerfile.agen-runtime>",<base_commit>,<golden_commit>,<test_commit>,"<полное содержимое run-tests-eval.sh>",feature,standard-library,git reset --hard <base_commit>,1,4g,4g,FALSE,standard,,,,,,,,,,
```

---

## 8. Рантайм и валидация

Сборка и запуск из корня `base/`:

```bash
# Весь набор тестов
bash .agen-runtime/run-tests-eval.sh

# Точечный прогон по списку файлов (через запятую; для PHPUnit запускается ./vendor/bin/phpunit <файлы>)
bash .agen-runtime/run-tests-eval.sh "packages/io/tests/unit/ConcatReadHandleTest.php,packages/io/tests/unit/TeeWriteHandleTest.php"
```

Обязательно проверьте:
- **Docker собирается** по `Dockerfile.agen-runtime`, тесты исполняются внутри контейнера.
- **F2P-тесты:** падают **до** `[sol]` → проходят **после** `[sol]` (строгий переход fail → pass).
- **P2P-тесты:** проходят **и до, и после** решения.

> **Проверка самодостаточности (обязательно).** Дайте `problem_statement` + `base` независимому исполнителю или агенту, **не показывая** ваше решение, тесты и исходный PR. Он должен прийти к решению, которое проходит F2P/P2P. Если воспроизвести изменение по одной лишь постановке не получается — дорабатывайте `problem_statement`, иначе задача не засчитывается.

---

## 9. Критерии приёмки

Задача будет **отклонена**, если выполнится хотя бы одно:

- ❌ **агент не может воспроизвести изменение и пройти F2P/P2P, имея на входе только `problem_statement` + `base` (без вашего решения, тестов и исходного PR) — решение НЕ засчитывается;**
- ❌ Docker не собирается или не запускает тесты;
- ❌ F2P-тесты не дают строгий переход fail → pass;
- ❌ P2P-тесты падают в какой-либо момент;
- ❌ постановка задачи расплывчата или неполна;
- ❌ золотое решение не является корректным/полным решением заявленной постановки;
- ❌ нарушена структура/префиксы коммитов;
- ❌ тесты нестабильны (flaky) или недетерминированы.

---

## 10. Что должно быть в файлах (шаблоны)

Ниже — структура двух обязательных документов. Скопируйте шаблон в соответствующий файл и заполните своими данными.

### 10.1. `PROBLEM_STATEMENT.md`

Самодостаточная постановка задачи: по ней агент (и проверяющий) должны понять, **чего** не хватает / что неоптимально и **что именно** требуется сделать, не видя ни вашего решения, ни исходного PR. Должна содержать разделы:

- **Заголовок и шапка** — `instance_id`, `language`, `task_type`, `task_category`.
- **Problem Statement** — `Title`; `Current behavior` (как ведёт себя код на base, чего не хватает); `Reproduction steps` (как воспроизвести/продемонстрировать отсутствие функциональности); `Expected behavior` (что должно стать после реализации — подробно: какие классы/файлы появляются и какой публичный контракт у каждого: конструктор, поведение `read`/`write`/`close`, граничные случаи); `Files to create/modify`; `Files NOT to touch`; `Constraints`.
- **Hints** — ключевые файлы и места кода, которые стоит изучить.
- **Test Files** — списки Fail-to-Pass и Pass-to-Pass тестов.
- **Commits** — таблица итоговых коммитов (`base` → `[sol]` → `[f2p]` → `[meta]`).

````markdown
# Task: <короткий заголовок задачи>

**instance_id:** `php-standard-library__php-standard-library__740`
**language:** PHP
**task_type:** feature
**task_category:** <напр. io / refactor>

---

## Problem Statement

Title: <заголовок>

Current behavior:
<как код ведёт себя сейчас, на base-коммите, чего не хватает / что дублируется>

Reproduction steps:
1. <шаг>
2. <шаг>

Expected behavior:
<что должно быть после реализации; подробно — какие классы/файлы появляются,
какой публичный контракт у каждого (конструктор, read/write/close, поведение
на границах), какие самописные обёртки заменяются>

Files to create/modify:
- `packages/io/src/Psl/IO/<Class>.php` — <что появляется/меняется>

Files NOT to touch:
- <файлы/области, которые трогать нельзя>

Constraints:
- <ограничения: детерминизм, без слома публичного API существующих handle-ов,
  совместимость с интерфейсами Psl\IO и т. п.>

---

## Hints

<ключевые файлы и места кода, которые стоит изучить перед решением>

---

## Test Files

**Fail-to-Pass** (падают на base, проходят после решения):
- `packages/io/tests/unit/<...>Test.php`

**Pass-to-Pass** (проходят и до, и после):
- `packages/io/tests/unit/<...>Test.php`

---

## Commits

| SHA | Type | Message |
|-----|------|---------|
| `<sha>` | base | php-standard-library на коммите перед PR #740 |
| `<sha>` | [sol] | <код решения> |
| `<sha>` | [f2p] | <fail-to-pass тесты> |
| `<sha>` | [meta] | metadata.json |
````

### 10.2. `PR_DESCRIPTION.md`

Описание PR золотого решения. Должно содержать разделы:

- **Заголовок** — `# [GOLDEN SOLUTION] <заголовок задачи>`.
- **Problem** — чего не хватало / что дублировалось на base.
- **Approach** — как работает ваше решение; отдельным блоком — ключевые отличия/улучшения относительно исходного PR; таблица изменённых файлов (`NEW`/`MOD`/`DEL`).
- **Testing Strategy** — списки F2P/P2P и что именно покрыто (сценарии, граничные случаи).
- **Commit Structure** — итоговые коммиты `[sol]` → `[f2p]` → `[meta]`.

````markdown
# [GOLDEN SOLUTION] Add composable IO handle decorators

## Problem

<чего не хватало / что дублировалось на base-коммите>

## Approach

<как работает ваше решение>

Key decisions vs. the original PR:
- <чем ваше решение отличается/лучше оригинального PR #740>

**Files changed:**

| Status | File |
| ------ | ---------------------------------- |
| NEW    | `packages/io/src/Psl/IO/<Class>.php` |
| MOD    | `packages/io/src/Psl/IO/<Class>.php` |

## Testing Strategy

**Fail-to-Pass** (`packages/io/tests/unit/<...>Test.php`):
- падают на base → проходят после `[sol]`

**Pass-to-Pass** (регрессионные, проходят до и после):
- `packages/io/tests/unit/<...>Test.php`

<что именно покрыто: ключевые сценарии и граничные случаи>

## Commit Structure

```
<sha> [sol]: <код решения>
<sha> [f2p]: <fail-to-pass тесты>
<sha> [meta]: metadata.json
```
````

---

### Ключевой принцип

> Вы не реализуете фичу. Вы проектируете качественную оценочную задачу, которая проверяет,
> сможет ли ИИ воспроизвести это изменение.
