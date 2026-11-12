# Каркас лекції

Скопіюйте теку в `lectures/<slug>/`. Специфікація: `kit/ENGINE.md`. JSON коментарів не має, тому пояснення тут.

## lecture.json
- `kicker` — службовий рядок угорі кожної сцени (вимкнути: `"kicker": false` у сцені; або `"kicker": "n2"` — час появи виразом).
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
- Сцена без малюнка: не додавайте `art.svg`, `parts`, `labels`; задайте `duration`, якщо немає реплік.
- `style.css` у теці сцени (необов'язково) доповнює `kit/theme/base.css`.

## Команди
`node kit/lecture.js lectures/<slug> plan | tts | qa | render | status`, `still <сцена> <час>`.
