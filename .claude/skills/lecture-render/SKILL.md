---
name: lecture-render
description: Зібрати лекцію у відеофайл MP4 з голосом і субтитрами. Використовувати, коли сцени пройшли перевірку.
argument-hint: <тека лекції>
context: fork
agent: render-runner
---

З кореня репозиторію по черзі: `node kit/lecture.js $0 plan`, `node kit/lecture.js $0 qa`, `node kit/lecture.js $0 tts`, `node kit/lecture.js $0 render`. Після першої ж помилки зупинись і поверни її. Якщо все пройшло — поверни шлях до MP4, тривалість і попередження з `plan`.
