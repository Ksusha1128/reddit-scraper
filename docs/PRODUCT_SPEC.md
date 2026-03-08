# 📋 Reddit Review Analyzer — Спецификация продукта v2

> **Цель:** Инструмент для product-аналитика, который позволяет **читать, исследовать, структурировать и действовать** на основе отзывов реальных юзеров из Reddit.

> **Ревью v2:** Учтены правки продакт-аналитика с 8+ лет опыта в CustDev.
> Добавлены: Data Pipeline, LLM-слой, SQLite модель данных, AI-фичи, Roadmap MVP→v1→v2.

---

## 📚 Источники и методологии

| Источник | Что взяли |
|----------|-----------|
| **Teresa Torres — "Continuous Discovery Habits"** | Opportunity Solution Tree: боли = opportunities, фичи = solutions. Интервью через story-based подход. Opportunity Mapping для структуризации пространства болей |
| **Intercom — "Customer Feedback Strategy"** | 7-step analysis: Collate → Categorize (type + theme + code) → Overview → Code → Refine → Count → Summarize. Приоритизация по volume + repetition + stakes |
| **NNGroup — "Dashboards: Preattentive Processing"** | Operational vs Analytical dashboards. Линейные графики > pie charts. Length + 2D position = лучшие visual encodings. Цвет — для категорий, не для количества |
| **NNGroup — "Filters vs Facets"** | Faceted navigation: множественные фильтры по разным измерениям контента. Фильтры описывают пространство данных и помогают понять что доступно |
| **Geckoboard — "Dashboard Design: 12 Tips"** | Data-ink ratio (убрать мусор). Группировка связанных метрик. Иерархия через размер/позицию. Контекст для чисел. Evolve dashboards итеративно |
| **Edward Tufte — "The Visual Display of Quantitative Information"** | Maximize data-ink ratio. Chartjunk = враг. Каждый пиксель должен нести информацию |
| **JTBD Framework (Clayton Christensen)** | Jobs-to-be-Done: юзеры "нанимают" продукт для задачи. Боли = unmet needs при выполнении Job |
| **Strategyzer — Pain-Gain Canvas** | Pain Relievers vs Gain Creators. Структуризация болей по severity и frequency |

---

## 🔴 MUST-FIX: Критические дополнения v2

### MF-1: Data Pipeline (парсер → хранилище → обогащение)

> **Проблема:** Парсер не описан, кнопка "Запустить" в TAB 6 — наивно. Reddit API 2025+ ужесточён.
> **Что уже есть в коде:** `export/database.py` (SQLite: posts, comments, subreddits, scheduled_jobs), `scraper/async_scraper.py` (aiohttp, reddit.com JSON), `src/scraper/` (RSS + http_client).

#### Архитектура Data Pipeline
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  1. SOURCES  │ ──→ │  2. INGEST   │ ──→ │ 3. ENRICH    │ ──→ │  4. STORE    │
│              │     │              │     │              │     │              │
│ • Reddit RSS │     │ • Dedup by   │     │ • VADER sent │     │ • SQLite     │
│   (primary)  │     │   post_id +  │     │ • Categorize │     │   (MVP)      │
│ • Reddit     │     │   comment_id │     │ • Segment    │     │ • all_reviews│
│   JSON API   │     │ • Incremental│     │ • Pain/feat  │     │   .csv       │
│ • PRAW       │     │   sync (via  │     │   extract    │     │   (backup)   │
│   (future)   │     │   `after`)   │     │ • LLM enrich │     │              │
│              │     │              │     │   (v1)       │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

#### Что уже реализовано ✅
- `export/database.py`: SQLite с таблицами `posts`, `comments`, `subreddits`, `scheduled_jobs`, `job_history` — **полностью рабочее**, с `UNIQUE` constraints
- `scraper/async_scraper.py`: aiohttp скрейпер через reddit.com JSON (не API) — обходит rate limits
- `src/scraper/rss_parser.py`: RSS фид парсер
- `src/analytics/categorizer.py`: keyword-based категоризация (10 категорий)
- `src/analytics/segments.py`: 6 сегментов с keyword + sentiment matching
- `src/analytics/pain_extractor.py`: regex-based extraction (13 pain patterns, 8 feature patterns, 7 positive patterns)

#### Что нужно доделать 🔄
1. **Incremental sync**: использовать `after` parameter + `last_scraped` из `subreddits` таблицы → не тянуть всё заново
2. **Dedup**: уже есть `UNIQUE` constraint на `permalink` и `comment_id` — нужно обработать `IntegrityError` gracefully
3. **Sync status в UI**: "Last synced: 22.02.2026 · 237 новых · 1270 всего"
4. **Schedule**: `scheduled_jobs` таблица уже есть — подключить к `APScheduler` или cron

#### MVP Pipeline (реализуем сейчас)
```python
# Простой sync flow:
1. RSS + JSON fetch (уже работает)
2. Dedup by post_id/comment_id (SQLite UNIQUE)
3. VADER sentiment (уже работает)
4. Keyword categorization (уже работает)
5. Keyword segmentation (уже работает)
6. Regex pain/feature extraction (уже работает)
7. Save to SQLite + CSV export
```

#### v1 Pipeline (после MVP)
```python
# LLM-enriched flow:
1. ... всё из MVP ...
2. LLM call (Claude/Groq/Together):
   - Zero-shot pain extraction (JTBD style)
   - Feature request extraction
   - User segment classification
   - Severity score (1-5)
   - Thread summary
3. Store as JSON columns in SQLite
```

### MF-2: LLM-слой для автоматической категоризации

> **Проблема:** Regex/keyword extraction в `pain_extractor.py` — ок для MVP, но не скалируется.
> **Решение:** Добавить LLM-слой как **optional enrichment** поверх существующего keyword-based.

#### Архитектура (2 уровня)
```
Level 1 (MVP — СЕЙЧАС):
  pain_extractor.py (regex) + segments.py (keywords) + categorizer.py (keywords)
  → Быстро, бесплатно, 100% offline

Level 2 (v1 — ПОТОМ):
  LLM API (Claude 3.5 Haiku / Groq Llama-3.1-70B)
  → Точнее, JTBD-стиль, severity, но стоит деньги + latency
```

#### Что LLM добавит (v1)
```python
# Для каждого review:
{
    "pains": [
        {"text": "App crashes on login", "severity": 4, "jtbd": "Use app reliably"},
    ],
    "feature_requests": [
        {"text": "Dark mode", "priority": "high"},
    ],
    "segment": "frustrated",
    "summary": "User frustrated with crashes after iOS update",
    "sentiment_nuance": "angry but willing to stay if fixed"
}
```

#### Стоимость
- Claude 3.5 Haiku: ~$0.001 per review → 1270 reviews = $1.27
- Groq Llama-3.1-70B: бесплатно до 30 req/min
- **Вывод:** не блокер, но не включать в MVP

### MF-3: Модель данных

> **Проблема:** Сейчас `all_reviews.csv` — flat file. Нет связи пост→комменты, нет `post_id`.
> **Что уже есть:** `export/database.py` имеет SQLite с нормализованной схемой (posts + comments + FK).

#### План
```
MVP: Продолжаем работать с all_reviews.csv
     + Добавляем post_id/comment_id колонки при следующем скрейпе
     + SQLite уже инициализирована — начинаем писать туда параллельно

v1:  SQLite = primary storage
     all_reviews.csv = export-only (кнопка в Настройках)
     Добавляем колонки: extracted_pains (JSON), user_segment, llm_summary
```

#### Текущие колонки CSV
```
app_name, source, author, title, text, subreddit, permalink, date,
sentiment_score, sentiment_label, categories, primary_category
```

#### Целевые колонки SQLite (v1)
```sql
-- Добавить к существующей схеме в export/database.py:
ALTER TABLE posts ADD COLUMN niche TEXT;
ALTER TABLE posts ADD COLUMN app_name TEXT;
ALTER TABLE posts ADD COLUMN extracted_pains TEXT;  -- JSON array
ALTER TABLE posts ADD COLUMN extracted_features TEXT;  -- JSON array
ALTER TABLE posts ADD COLUMN user_segment TEXT;
ALTER TABLE posts ADD COLUMN llm_summary TEXT;
ALTER TABLE posts ADD COLUMN severity INTEGER;
```

---

## 🟠 SHOULD-FIX: AI-фичи и улучшения

### SF-1: AI-кнопки в интерфейсе (v1)

| Таб | Кнопка | Что делает |
|-----|--------|-----------|
| TAB 1 Отзывы | "📝 Summarize thread" | LLM суммаризирует пост + все комменты → 2-3 предложения |
| TAB 2 Боли | "❓ Генерировать вопросы (Torres)" | LLM создаёт 5 story-based вопросов для интервью по конкретной боли |
| TAB 3 Юзеры | "✉️ Персональный DM" | LLM пишет DM на основе 2-3 постов юзера |
| TAB 2 Боли | "🌳 Opportunity Tree" | Экспорт топ-болей + решений в формате OST |

> **MVP:** Без AI-кнопок. Только regex/keyword extraction.
> **v1:** Добавить кнопки. Groq API (бесплатный tier) или Claude Haiku.

### SF-2: Semantic Search (v2)

```
MVP: str.contains() — точное совпадение подстроки
v1:  Тот же str.contains() но с fuzzy matching (fuzzywuzzy)
v2:  Embeddings + ChromaDB/LanceDB — семантический поиск
```
> Пользователь ищет "приложение крашится после обновления" → находит "app broke after update".

### SF-3: Anomaly Detection в Трендах (v2)

```
v2: Если sentiment падает >0.15 за неделю:
    → Красная точка на графике
    → Notification в Telegram/Slack (опционально)
```

### SF-4: Расширенный экспорт (v1)

```
MVP: CSV + Excel (встроенный st.dataframe download)
v1:  + "Copy as Markdown" (для Confluence/Notion)
     + "Export Opportunity Canvas PDF"
v2:  + Notion API integration
     + Jira/Productboard/Canny integration
```

---

## 🟢 NICE-TO-HAVE

- [ ] Light mode toggle (`.streamlit/config.toml` переключение)
- [ ] Collapsible comment tree (вместо flat list) — нужен `parent_id` в данных
- [ ] "What changed since last sync" — фильтр по дате последнего sync
- [ ] Интеграция с Productboard/Jira/Canny ("Create feature from pain")
- [ ] `st.fragment()` для пагинации без перерендера всего dashboard
- [ ] DuckDB вместо pandas для больших данных (`duckdb.read_parquet`)

---

## 🎯 Ключевые принципы

### 1. Текст — король
> Аналитик хочет **читать реальные слова юзеров**. Графики — это summary. Тексты — это data.

- Каждый отзыв = полный текст + контекст (автор, дата, приложение, тональность, ссылка)
- Progressive disclosure: сначала заголовок → раскрыть → полный текст → комментарии
- Поиск по тексту — must have (grep по реальным словам юзеров)

### 2. Data-ink ratio
> Каждый элемент на экране должен нести информацию. Убрать всё декоративное.

- Нет pie charts, radar charts, gauge charts (NNGroup: "area-based graphs are difficult to interpret")
- Нет бесполезных общих метрик ("всего 1270 отзывов" — и что?)
- Только bar charts (length = preattentive) и line charts (2D position = preattentive)

### 3. Фильтры = навигация
> Faceted navigation: фильтры по нескольким измерениям одновременно (NNGroup)

- Приложение, Тематика, Тональность, Тип (пост/коммент), Период, Поиск по тексту
- Фильтры в top bar — всегда видны, компактные
- Фильтры работают **глобально на все табы**

### 4. Progressive disclosure
> Показывай мало → пользователь раскрывает → получает глубину (Geckoboard: "hierarchy through size and position")

- Список постов → клик → полный текст + комментарии
- Боль → клик → цитаты юзеров
- Юзер → клик → все его отзывы

### 5. Actionability
> Каждый блок должен вести к действию (Teresa Torres: "discovery → action")

- Боль → "Что делать?" → Outreach к frustrated users
- Юзер → Ссылка на профиль → DM
- Конкурент → Strengths/Weaknesses → Продуктовое решение

---

## 🏗️ Архитектура табов

### TAB 1: 📝 Отзывы (ГЛАВНЫЙ)
> **Назначение:** Чтение, поиск, исследование реальных текстов юзеров.
> **Принцип:** Это 80% работы аналитика. Всё остальное — вторично.

#### Верхний блок: Глобальные фильтры
```
[ Тематика ▼ ] [ Приложение ▼ ] [ Тональность ▼ ] [ Тип ▼ ] [ Период ▼ ] [ 🔍 Поиск по тексту ]
```

#### Compact stat line
```
234 отзывов · +0.34 тональность · 12 приложений · 4 тематики
```
> Без карточек, без больших цифр. Одна строка (Geckoboard: "give numbers context", но compact).

#### Переключатель вида
```
◉ Посты + комментарии   ○ Таблица
```

#### Вид "Посты + комментарии" (DEFAULT)
```
┌─────────────────────────────────────────────────────────┐
│ ▶ App won't sync after update — BetterHelp · 12.01.26  │
│   😞 негатив · 💬 3 комментария                         │
├─────────────────────────────────────────────────────────┤
│ ▼ Switched from Calm to Headspace — Calm · 05.01.26    │
│   😊 позитив · 💬 7 комментариев                        │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Текст поста: "I've been using Calm for 2 years     │ │
│ │ but recently switched to Headspace because..."      │ │
│ │                                                     │ │
│ │ 🔗 Открыть на Reddit  ·  u/mindful_user            │ │
│ │                                                     │ │
│ │ ── 💬 Комментарии ──────────────────────────────── │ │
│ │ │ u/zen_master · 😊 позитив                        │ │
│ │ │ "I made the same switch! Headspace's sleep..."   │ │
│ │ │                                                   │ │
│ │ │ u/calm_fan · 😞 негатив                          │ │
│ │ │ "Disagree, Calm has better music selection..."   │ │
│ └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│ ▶ Best calorie tracking app 2026? — General · 28.12.25 │
│   😐 нейтрал · 💬 12 комментариев                      │
└─────────────────────────────────────────────────────────┘
```

**Ключевые элементы поста:**
- Заголовок (полный, не обрезанный)
- Приложение + дата + тональность (pill badges)
- Кол-во комментариев
- При раскрытии: полный текст + мета + комменты
- Ссылка на оригинал Reddit
- Пагинация (30 постов на страницу)
- **v1:** Кнопка "📝 Summarize" → LLM суммаризирует пост + комменты в 2-3 предложения

#### Вид "Таблица"
- `st.dataframe` с колонками: Приложение, Заголовок, Текст, Тональность, Автор, Дата, Ссылка
- Встроенная сортировка и скачивание (CSV)
- Без кастомных кнопок экспорта (Streamlit имеет встроенный CSV download)

#### Поиск по тексту
- Input field в фильтрах: `🔍 Поиск по тексту`
- Фильтрует посты и комменты где text содержит запрос (case-insensitive)
- Подсветка найденного в тексте (через HTML `<mark>`)

---

### TAB 2: 😤 Боли & Запросы
> **Назначение:** Тексты юзеров, структурированные по болям и фич-реквестам.
> **Принцип:** Не графики, а тексты. Боль = тема + реальные цитаты (Intercom: "feedback code" + "feedback theme").
>
> **MVP:** Regex/keyword extraction (`pain_extractor.py` — 13 pain patterns, 8 feature patterns).
> **v1:** LLM zero-shot extraction (JTBD-стиль, severity 1-5). Кнопка "Генерировать вопросы".

#### Структура
```
┌──────────────────────────────────────┬──────────────────────────────────────┐
│ 😤 ТОП БОЛЕЙ                        │ 💡 ФИЧ-РЕКВЕСТЫ                     │
│                                      │                                      │
│ ▶ App crashes on Android (23 упом.)  │ ▶ Dark mode support (18 упом.)       │
│ ▶ Can't sync between devices (19)    │ ▶ Export data feature (12)           │
│ ▶ Subscription too expensive (17)    │ ▶ Offline mode (9)                   │
│ ▶ Poor customer support (14)         │                                      │
│                                      │                                      │
│ ▼ Notifications don't work (11)      │                                      │
│ ┌──────────────────────────────────┐ │                                      │
│ │ Цитаты:                         │ │                                      │
│ │ • "Push notifications stopped   │ │                                      │
│ │   working after the last..."    │ │                                      │
│ │   — BetterHelp, u/anxious_user │ │                                      │
│ │                                  │ │                                      │
│ │ • "I set reminders but they     │ │                                      │
│ │   never fire. Very frustrating" │ │                                      │
│ │   — Calm, u/meditation_daily   │ │                                      │
│ │                                  │ │                                      │
│ │ Приложения: BetterHelp, Calm,   │ │                                      │
│ │ Headspace                        │ │                                      │
│ └──────────────────────────────────┘ │                                      │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

**Каждая боль содержит:**
1. Название боли (краткое описание)
2. Кол-во упоминаний
3. При раскрытии:
   - 5-7 реальных цитат с автором и приложением
   - Список приложений где эта боль встречается
   - Ссылки на оригинальные посты

#### Что хвалят
```
😊 ЧТО ХВАЛЯТ
▶ Easy to use interface (31 упом.)
▶ Great meditation content (24)
▶ Helpful reminders (18)
```
> Те же раскрываемые блоки с цитатами.

#### Переключения между приложениями
```
🔄 ПЕРЕКЛЮЧЕНИЯ
┌──────────┬──────────┬─────────────────────────────────────┐
│ Откуда   │ Куда     │ Причина (цитата)                    │
├──────────┼──────────┼─────────────────────────────────────┤
│ Calm     │ Headspace│ "Better sleep stories and cheaper"  │
│ MyFitPal │ Cronometer│ "More accurate macro tracking"     │
└──────────┴──────────┴─────────────────────────────────────┘
```

#### AI-кнопки (v1)
```
[ ❓ Генерировать вопросы для интервью (Torres) ] → LLM создаёт 5 story-based вопросов по выбранной боли
[ 🌳 Экспорт Opportunity Tree ]                   → Топ боли + фичи в формате OST (markdown)
```

---

### TAB 3: 👥 Юзеры
> **Назначение:** Найти юзеров для CustDev, интервью, outreach.
> **Принцип:** Teresa Torres — "interview customers continuously, week over week". Reddit = источник респондентов.

#### Сегменты юзеров
```
😤 Frustrated (45)  ·  🔍 Searchers (23)  ·  💰 Price-sensitive (18)  ·  🔄 Switchers (12)  ·  ⭐ Advocates (31)  ·  🆕 New users (28)
```

#### Каждый сегмент раскрывается:
```
▼ 😤 Frustrated — 45 отзывов (28 юзеров)
  Описание: Юзеры с негативными отзывами, жалобами на баги и UX
  
  Топ юзеры:
  • u/angry_user — 5 отзывов · BetterHelp, Calm [👤 Профиль] [✉️ DM]
  • u/bugs_everywhere — 3 отзыва · Headspace [👤 Профиль] [✉️ DM]
  
  Примеры текстов:
  • "The app crashes every time I try to..." — BetterHelp
  • "Paid $60/year and can't even get basic features to work" — Calm
  
  Приложения: BetterHelp (18), Calm (12), Headspace (8)
```

#### Таблица для outreach
| Юзер | Приложение | Сегмент | Тональность | Текст (превью) | Профиль | DM |
|------|-----------|---------|-------------|-----------------|---------|-----|
| u/angry_user | BetterHelp | 😤 Frustrated | 😞 -0.8 | "App crashes every..." | [открыть] | [написать] |

#### Шаблоны DM
В expander — 3 шаблона для разных сегментов (Frustrated, Searcher, Price-sensitive).
Простой текст, копируемый.

**v1:** Кнопка "✉️ Персональный DM" → LLM пишет DM на основе 2-3 последних постов юзера.

---

### TAB 4: ⚔️ Конкуренты
> **Назначение:** Сравнение приложений между собой. Competitive Intelligence.

#### Сравнительная таблица
| Приложение | Отзывов | Ср. тональн. | Позитив % | Негатив % | Топ боль | Топ хвалят |
|-----------|---------|-------------|-----------|-----------|----------|-----------|

#### Тональность по приложениям (ср. балл)
> Горизонтальный bar chart — ЕДИНСТВЕННЫЙ обязательный график.
> Цвет: зелёный (>0.05), красный (<-0.05), жёлтый (нейтрал).

#### Сильные / Слабые стороны
Каждое приложение → expander:
- ✅ Хвалят: easy to use, great content, ...
- ❌ Ругают: expensive, buggy, poor support, ...

#### Переключения (повтор из Болей, но сфокусирован на конкурентов)

---

### TAB 5: 📊 Тренды
> **Назначение:** Как меняется sentiment во времени. Что растёт, что падает.

#### Тональность во времени (line chart)
- X: дата (по неделям/месяцам)
- Y: средний sentiment score
- Линии: по приложениям или по тематикам
- Hover: точные значения

#### Объём отзывов во времени (bar chart)
- X: дата
- Y: кол-во отзывов
- Stacked по тональности (pos/neu/neg)

#### Активность по сабреддитам
- Горизонтальный bar chart: top-10 сабреддитов по кол-ву отзывов

> **Нет:** pie charts, radar charts, word clouds (low information density).
> N-граммы и TF-IDF — убрать в expander "Продвинутая аналитика" для тех кому нужно.
>
> **v2:** Anomaly detection — красные точки когда sentiment падает >0.15 за неделю + Telegram/Slack alert.

---

### TAB 6: ⚙️ Data Pipeline & Настройки
> **Назначение:** Управление данными: синхронизация, мониторинг pipeline, экспорт, конфигурация.
> **Принцип:** Pipeline = сердце инструмента. Если данные не свежие — всё остальное бесполезно.

#### Sync Status (всегда видно вверху таба)
```
🟢 Последний sync: 22.02.2026 04:12 · 237 новых · 1270 всего · SQLite: 4.2 MB
```

#### Управление sync
```
┌────────────────────────────────────────────────────────┐
│ Тематика: [ Все ▼ ]   Лимит постов: [ 50 ]            │
│                                                        │
│ [ ▶ Sync now ]  [ 🔄 Schedule: ежедневно 3:00 ]       │
│                                                        │
│ ⚠️ Force full refresh (пересканировать всё) — expander │
└────────────────────────────────────────────────────────┘
```

#### Pipeline Log (в expander)
```
▶ 📋 История синхронизаций
  22.02.2026 04:12 — 237 новых постов, 89 комментов, 0 ошибок (42s)
  21.02.2026 04:08 — 12 новых постов, 3 коммента, 0 ошибок (8s)
  20.02.2026 04:15 — 156 новых, 2 ошибки (timeout r/BetterHelp)
```

#### Экспорт (в expander)
```
▶ 📥 Экспорт данных
  [ Excel ] [ CSV ] [ Copy as Markdown ]
```

#### Отслеживаемые приложения
Таблица: Тематика, Приложение, Поисковые запросы

#### Enrichment Status (v1 — после подключения LLM)
```
▶ 🤖 LLM Enrichment
  Provider: [ Groq (free) ▼ ]
  Enriched: 890/1270 (70%) · Not enriched: 380
  [ ▶ Enrich new reviews ]
```

---

## 🎨 Дизайн-система

### Цветовая палитра (Grafana Dark)
```
Canvas:     #111217   (фон)
Primary:    #181b1f   (карточки, panels)
Secondary:  #1e2028   (inputs, hover)
Border:     #2c3235   (разделители)
Text:       #d8d9da   (основной текст)
Text Dim:   #8e8e8e   (мета-информация)
Blue:       #5794f2   (ссылки, акценты)
Green:      #73bf69   (позитив)
Red:        #f2495c   (негатив)
Yellow:     #ff9830   (нейтрал, warning)
Purple:     #b877d9   (категории)
```

### Типографика
- Заголовки: 500 weight, `#d8d9da`
- Мета-текст: 0.78rem, `#8e8e8e`, uppercase
- Тело отзыва: 0.85rem, `#d8d9da`, line-height 1.5
- Pills/Tags: 0.72rem, 500 weight, border-radius 3px

### Компоненты
| Компонент | Когда использовать |
|-----------|-------------------|
| **Expander** | Посты → раскрыть → текст + комменты. Боли → раскрыть → цитаты |
| **Pills/Tags** | Тональность (😊/😞/😐), тип (пост/коммент), приложение, сабреддит |
| **Stat line** | Compact одна строка с ключевыми цифрами + `·` separators |
| **Bar chart** | Сравнение количеств (приложения, боли). ТОЛЬКО горизонтальный |
| **Line chart** | Тренды во времени |
| **Table** | Сравнительные данные, outreach-таблица |
| **Карточка** | НЕ использовать для KPI. Только для отзывов/цитат |

### Анти-паттерны (НЕ ДЕЛАТЬ)
| ❌ Анти-паттерн | Почему | Источник |
|----------------|--------|---------|
| Pie chart | Area-based, трудно сравнивать | NNGroup |
| Radar chart | Сложно интерпретировать | NNGroup |
| Большие KPI-карточки | Занимают место, мало информации | Geckoboard: "data-ink ratio" |
| Большие кнопки экспорта | Визуальный мусор | Tufte: "chartjunk" |
| Word cloud | Красиво, но 0 actionable insights | — |
| 3D графики | Distort data perception | NNGroup |
| Дублирование данных в разных форматах | Scatter attention | Geckoboard: "be consistent" |

---

## 🔬 Workflow аналитика (User Story)

### Сценарий 1: Исследование нового рынка
```
1. Открыть вкладку "Отзывы"
2. Фильтр: Тематика = "🧠 AI-психолог"
3. Читать посты, раскрывать комментарии
4. Переключиться на "Боли" → увидеть топ болей для этой ниши
5. Раскрыть боль → прочитать реальные цитаты
6. Перейти на "Конкуренты" → сравнить приложения
7. Найти: BetterHelp = -0.12, Calm = +0.34 → инсайт: BetterHelp отстаёт
```

### Сценарий 2: Поиск респондентов для CustDev
```
1. Вкладка "Юзеры"
2. Сегмент: Frustrated
3. Фильтр: Приложение = "MyFitnessPal"
4. Найти юзеров с 3+ отзывами
5. Прочитать их тексты → понять контекст
6. Кликнуть [DM] → открыть Reddit → отправить шаблон
```

### Сценарий 3: Мониторинг конкурентов
```
1. Вкладка "Тренды"
2. Выбрать 3 конкурента
3. Смотреть sentiment trend за последние 3 месяца
4. Заметить падение у конкурента X
5. Перейти на "Отзывы" → фильтр по X → прочитать что случилось
```

### Сценарий 4: Подготовка к интервью
```
1. Вкладка "Боли" → выбрать тематику
2. Выписать топ-5 болей с цитатами
3. Сформулировать story-based вопросы:
   "Расскажите о последнем разе когда вы [столкнулись с болью X]"
4. Вкладка "Юзеры" → найти 5-10 респондентов
5. Использовать шаблон DM для outreach
```

---

## 🔗 Интервью и CustDev через инструмент

### Как находить респондентов
1. **Frustrated users** → негативные отзывы + активные юзеры → прямой DM на Reddit
2. **Searchers** → "Looking for an app that..." → человек ищет решение → идеальный респондент
3. **Switchers** → "Switched from X to Y because..." → знает рынок, готов говорить
4. **Активные комментаторы** → 5+ отзывов → глубоко вовлечены в тему

### Как проводить интервью (Teresa Torres)
1. **Story-based questions:** "Tell me about the last time you..."
2. **Не спрашивать "что бы вы хотели"** — спрашивать о реальном прошлом опыте
3. **Opportunity mapping:** каждый инсайт → opportunity на дереве
4. **Continuous:** минимум 1 интервью в неделю

### Workflow в инструменте
```
Инструмент                          → Действие
─────────────────────────────────────────────────────
Боли + Цитаты                       → Гипотезы для вопросов
Юзеры (Frustrated/Searchers)        → Список респондентов
DM шаблон                           → Первое сообщение
Ссылка на профиль                   → Проверить активность
Отзывы юзера                        → Контекст перед интервью
Конкуренты (strengths/weaknesses)    → Понимание рынка
```

---

## 📐 Technical Implementation Notes

### Streamlit 1.54 specifics
- `width="stretch"` (не `use_container_width`, deprecated)
- `.streamlit/config.toml` с `[theme] base="dark"` — нативные тёмные таблицы
- `st.dataframe` с `column_config` для ссылок
- `st.expander` для progressive disclosure
- Глобальные CSS через `st.markdown(unsafe_allow_html=True)`
- **`st.fragment()`** для пагинации и expanders (не перерендерить весь дашборд)
- Custom pills через HTML `<span>` (не дефолтные `st.pills`)
- `<mark>` подсветка поиска через `unsafe_allow_html`

### Performance
- `@st.cache_data(ttl=3600)` для загрузки данных (увеличен с 120s)
- Пагинация постов (30 на страницу) — не рендерить 1000+ expanders
- Текстовый поиск: `str.contains()` на DataFrame (MVP), semantic search (v2)
- **v2:** DuckDB вместо pandas для больших данных (`duckdb.read_parquet`)

### Что уже есть в codebase и переиспользуем
```
src/analytics/pain_extractor.py  → TAB 2 (боли, фичи, что хвалят)
src/analytics/segments.py        → TAB 3 (6 сегментов юзеров)
src/analytics/categorizer.py     → Категоризация по ReviewCategory enum
src/analytics/competitor.py      → TAB 4 (comparison table, switches, strengths)
src/analytics/patterns.py        → TAB 5 expander (ngrams, tfidf, word freq)
src/analytics/sentiment.py       → VADER sentiment scoring
src/survey/collector.py          → CustDev survey collection
src/survey/templates.py          → DM шаблоны
export/database.py               → SQLite (posts, comments, jobs, alerts)
scraper/async_scraper.py         → aiohttp Reddit JSON scraper
src/scraper/rss_parser.py        → RSS feed parser
src/scraper/http_client.py       → HTTP client with retries
src/models.py                    → Pydantic models (Review, AppConfig, etc.)
src/apps.py                      → 36 apps across 5 niches
```

### Data flow
```
                          ┌──────────────────────┐
                          │   Reddit (RSS/JSON)  │
                          └──────────┬───────────┘
                                     ↓
                          ┌──────────────────────┐
                          │  scraper/ + src/     │
                          │  scraper/            │
                          └──────────┬───────────┘
                                     ↓
                    ┌────────────────┬────────────────┐
                    ↓                                 ↓
            ┌──────────────┐                ┌──────────────┐
            │   SQLite     │                │   CSV        │
            │ (primary v1) │                │ (backup)     │
            └──────┬───────┘                └──────┬───────┘
                   ↓                               ↓
            ┌──────────────────────────────────────────┐
            │           load_reviews()                  │
            │         @st.cache_data(ttl=3600)         │
            └──────────────────┬───────────────────────┘
                               ↓
                     ┌──────────────────┐
                     │  _top_filters()  │
                     │  (global facets) │
                     └────────┬─────────┘
                              ↓
          ┌───────┬───────┬───────┬───────┬───────┐
          ↓       ↓       ↓       ↓       ↓       ↓
        TAB1    TAB2    TAB3    TAB4    TAB5    TAB6
       Отзывы  Боли   Юзеры  Конкур  Тренды Pipeline
```

---

## 🗓️ Roadmap: MVP → v1 → v2

### MVP (2-3 недели) — СЕЙЧАС ДЕЛАЕМ
> Цель: рабочий инструмент для чтения текстов + базовая аналитика.

- [x] Скрейпер (RSS + JSON, 1270 отзывов собрано)
- [x] VADER sentiment
- [x] Keyword categorization (10 категорий)
- [x] Regex pain/feature/highlight extraction
- [x] 6 user segments (keyword + sentiment)
- [x] Competitor comparison table + switches detection
- [x] 36 apps × 5 niches configured
- [x] 46 tests passing
- [ ] **TAB 1: Отзывы** — посты + комменты + поиск + пагинация
- [ ] **TAB 2: Боли** — regex extraction + цитаты
- [ ] **TAB 3: Юзеры** — сегменты + outreach таблица + DM шаблоны
- [ ] **TAB 4: Конкуренты** — таблица + bar chart + strengths/weaknesses
- [ ] **TAB 5: Тренды** — sentiment line chart + volume bar chart
- [ ] **TAB 6: Pipeline** — sync status + sync now + export
- [ ] Глобальные фильтры (6 измерений)
- [ ] Grafana dark theme (CSS + config.toml)

### v1 (+3 недели после MVP)
> Цель: LLM-обогащение + AI-кнопки + SQLite primary.

- [ ] LLM integration (Groq free tier / Claude Haiku)
- [ ] Auto-categorization болей (zero-shot JTBD)
- [ ] AI кнопки: Summarize, Generate Questions, Personal DM
- [ ] Opportunity Solution Tree export
- [ ] SQLite = primary storage (CSV = backup export)
- [ ] Incremental sync + dedup
- [ ] Scheduled sync (daily 3 AM)
- [ ] Copy as Markdown export
- [ ] `st.fragment()` для partial rerenders

### v2 (backlog)
> Цель: semantic search + anomalies + integrations.

- [ ] Semantic search (embeddings + ChromaDB/LanceDB)
- [ ] Anomaly detection (sentiment drops) + Telegram/Slack alerts
- [ ] Notion API export
- [ ] Jira/Productboard/Canny integration
- [ ] Light mode toggle
- [ ] Collapsible comment trees (parent_id based)
- [ ] "What changed since last sync" filter
- [ ] DuckDB for large datasets

---

## ✅ Чеклист перед запуском MVP

- [ ] TAB 1 (Отзывы): посты раскрываются, комменты видны, поиск работает, пагинация
- [ ] TAB 2 (Боли): regex extraction + цитаты, фич-реквесты, что хвалят, переключения
- [ ] TAB 3 (Юзеры): сегменты, outreach таблица, DM шаблоны, ссылки на профили
- [ ] TAB 4 (Конкуренты): сравнительная таблица, sentiment bar chart, strengths/weaknesses
- [ ] TAB 5 (Тренды): sentiment over time line chart, volume bar chart
- [ ] TAB 6 (Pipeline): sync status, sync now, export, список приложений
- [ ] Фильтры: все 6 работают глобально на все табы
- [ ] Тёмная тема: нет белых фонов нигде
- [ ] Нет мусора: pie charts, radar, word clouds, big KPI cards, big export buttons
- [ ] Тесты проходят (46 тестов)
- [ ] `st.cache_data(ttl=3600)` для данных
- [ ] Custom CSS pills для тональности/приложений
- [ ] `<mark>` подсветка поиска

## 📊 Acceptance Criteria

### TAB 1 считается готовым когда:
1. Все 1270 отзывов загружаются < 2 сек
2. Фильтры по 6 измерениям работают одновременно
3. Пост раскрывается → виден полный текст + комменты + meta
4. Поиск по тексту находит и подсвечивает совпадения
5. Пагинация: 30 постов/страница, навигация prev/next

### TAB 2 считается готовым когда:
1. Минимум 10 болей извлечены с цитатами
2. Каждая боль раскрывается → 3-7 цитат с автором + приложением
3. Фич-реквесты и "Что хвалят" работают аналогично
4. Переключения показывают from→to + причину

### TAB 3 считается готовым когда:
1. Все 6 сегментов отображаются с количеством юзеров
2. Каждый сегмент раскрывается → топ юзеры + цитаты
3. Ссылки на Reddit профили работают
4. DM шаблоны копируемые
