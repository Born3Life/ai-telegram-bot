# Space Solitaire — Космический Пасьянс

## Как играть
Открой `index.html` в браузере. Всё.

## Правила (Клондайк)
- Раскладывай карты по мастям от Туза до Короля в 4 стопки вверху
- Внизу чередуй цвета по убыванию
- Клик по колоде — взять карту
- Тащи карту в столбец или в стопку
- Пустой столбец можно начать с Короля

## Промпты для генерации спрайтов (через /draw)

### Рубашки карт (скины)
Сохраняются в `assets/`

- **Скин: Классика** → `assets/back_classic.png`
  /draw Playing card back design, deep space theme, dark purple and blue with gold nebula swirl, clean symmetric pattern, game asset, 90x126

- **Скин: Неон** → `assets/back_neon.png`
  /draw Playing card back, cyberpunk space theme, neon cyan and magenta grid with stars, glowing circuit pattern, 90x126

- **Скин: Золото** → `assets/back_gold.png`
  /draw Luxurious playing card back, gold filigree on deep navy, royal space pattern, ornate border, elegant, 90x126

### Фон стола
- **Фон 1** → `assets/felt_dark.png`
  /draw Felt texture for card table, deep dark blue-green with subtle stars, seamless, 900x600

### Значки и UI
- **Иконка победы** → `assets/star_icon.png`
  /draw Golden glowing star icon, celestial, sharp edges, game UI element, 64x64

## Монетизация (Яндекс.Игры)
Kомментарии `// YG:` в коде — места для интеграции SDK:
- `ysdk.features.LoadingAPI.ready()` — старт
- `ysdk.adv.showFullscreenAdv()` — реклама после победы
- `ysdk.getPayments().purchase()` — покупка скинов
