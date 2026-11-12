---
name: lecture-render
description: Відрендерити варіант або сцену у відеофайл MP4. Використовувати, коли кадр пройшов перевірку.
argument-hint: <тека>
context: fork
agent: render-runner
---

З кореня репозиторію: спершу `node kit/render.js $0 qa`. Якщо є зауваження — зупинись і поверни їх. Якщо PASS — `node kit/render.js $0 video` і поверни шлях до MP4.
