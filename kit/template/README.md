# Каркас лекції

Скопіюйте теку в `lectures/<slug>/`. Специфікація: `kit/ENGINE.md`. JSON коментарів не має, тому пояснення тут.

## lecture.json
- `kicker` — службовий рядок угорі сцен (стара розкладка, `lectures/bronchi`). У нових лекціях (`"layout": "center"`) його не задають; у сцені можна вимкнути `"kicker": false`.
- Нові лекції: `"layout": "center"`, `artLimitKB` (типово 30; для малюнків «під рух» більше, напр. 64), `world.md` і `brief` у сценах — приклад `lectures/anemia/`.
- `voice.provider`: `estimate` (без звуку, `rate` символів/с), `beep`, `elevenlabs`, `piper`.
- `pronounce` — заміни перед синтезом; у субтитрах лишається вихідний текст.
- `credits: true` — наприкінці автоматична сцена зі списком `sources`.
- Розділи: `chapters[].scenes` — теки з `scenes/`; порядок = порядок у відео.

## scenes/01-intro/scene.json
- `narration` — репліки (`id` на кшталт n1); `gap` — пауза перед реплікою (типово 0,35 с); `[[id]]` у тексті — позначка миті для виразу `@id`.
- Часи (`at`, `in`, `out`): `start`, `end`, `n2`, `n2.end`, `@id`, плюс `+0.5`/`-0.3`, або число секунд.
- `states[].set`: `hidden`, `color`, `grey` для частин із `parts`. Те, про що мова, — `color`; решта — `grey`.
- `labels`: `anchor` — точка `<circle r="0">` в art.svg, `focus` — частина, поки кольорова видно підпис, `onArt` — підпис на малюнку без виноски.
- `texts[].kind`: hook, title, thesis, note, quiz (meta і source ставляться автоматично). Необов'язково: `x`, `y` (перевизначити місце), `enter`/`exit` (`fade`/`cut`), `class` (наприклад `k-answer` для відповіді quiz).
- `title`, що йде одночасно з `hook`, автоматично отримує клас `k-low` (нижче місце), тож тексти не накладаються.
- `sources` — рядки джерел унизу кадру з `lecture.json`; одночасні складаються стопкою.
- Сцена без малюнка — лише титри (`duration`, без реплік) і стара розкладка; у нових лекціях кожна сцена має малюнок.
- `style.css` у теці сцени (необов'язково) доповнює `kit/theme/base.css`.

## Рух і розкладка (див. ENGINE.md 3.6, 3.7)
- `lecture.json`: `"layout": "center"` — центрована розкладка: малюнок посередині, великий текст у нижній смузі (`"band": "top"` — у верхній).
- Наголос: `замо́к` (U+0301) у тексті репліки чи в `pronounce`; на екрані й у субтитрах знак прибирається.
- Зразок руху: `scenes/02-motion` (carry із різним малюнком, `draw`, `move`, `loop`, `camera` до `v-zone`, підпис за камерою) і `03-zoom` (carry з тим самим малюнком, камера назад до `camera0`, `count`). У `art.svg`: `<rect id="v-zone" fill="none" stroke="none">`, точки `pt-a`/`pt-b`.
- `node kit/lecture.js lectures/<slug> motion` — таблиця руху по сценах.

## Команди
`node kit/lecture.js lectures/<slug> plan | tts | qa | render | motion | status`, `still <сцена> <час>`. Одна сцена з попередніми: `kit/one-scene.sh lectures/<slug> <сцена>` → тимчасова тека для `qa`/`still`/`motion`.
