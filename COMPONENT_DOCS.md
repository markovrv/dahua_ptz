# Компонент Home Assistant — Dahua PTZ (v2.0)

## Что изменилось

Компонент переписан для работы через **CLI-скрипт** (`dahua_ptz_cli.py`) вместо прямого HTTP-взаимодействия. Это устраняет зависимость от `aiohttp` и `async_timeout`.

### Архитектура

```
Home Assistant
    │
    ▼
__init__.py (сервисы)
    │
    ▼ (subprocess, async_add_executor_job)
dahua_cli.py (обёртка)
    │
    ▼ (python dahua_ptz_cli.py ...)
dahua_ptz_cli.py (CLI)
    │
    ▼ (HTTP POST /RPC2)
Камера Dahua
```

---

## Установка

1. Скопируйте папку `custom_components/dahua_ptz` в ваш Home Assistant
2. Убедитесь, что `python` доступен в PATH системы
3. Перезапустите Home Assistant

---

## Конфигурация

### Через UI

**Настройки → Устройства и службы → Интеграции → Добавить → Dahua PTZ**

| Поле | Значение |
|---|---|
| Host | `192.168.1.114` |
| Username | `admin` |
| Password | `L2E3C8C0` |
| Script path | (оставьте пустым для автопоиска) |

### Через YAML (configuration.yaml)

```yaml
dahua_ptz:
  host: "192.168.1.114"
  username: "admin"
  password: "L2E3C8C0"
```

---

## Сервисы

### `dahua_ptz.move_relative`

Относительное перемещение на указанный угол.

```yaml
service: dahua_ptz.move_relative
data:
  direction: "left"    # left | right | up | down
  degrees: 90          # угол в градусах
```

### `dahua_ptz.move_absolute`

Переход к абсолютной позиции (Pan/Tilt в градусах).

```yaml
service: dahua_ptz.move_absolute
data:
  pan: 180             # горизонталь (0-360°)
  tilt: 45             # вертикаль (-90° — +90°)
```

### `dahua_ptz.go_home`

Возврат в домашнюю позицию (0, 0).

```yaml
service: dahua_ptz.go_home
```

### `dahua_ptz.ptz_control` (legacy)

Совместимость со старым API. Поддерживает только `PositionABS`.

```yaml
service: dahua_ptz.ptz_control
data:
  code: "PositionABS"
  arg1: 1800           # Pan в 0.1° (180.0°)
  arg2: 450            # Tilt в 0.1° (45.0°)
```

### `dahua_ptz.restart`

Перезагрузка интеграции.

```yaml
service: dahua_ptz.restart
```

---

## Трекер позиции

Компонент хранит последнюю известную позицию в файле `ptz_position.json` внутри папки компонента. Этот файл используется для расчёта относительного перемещения.

```json
{
  "pan": 2700,
  "tilt": 0,
  "zoom": 0
}
```

> **Значения в 0.1°:** `pan: 2700` = 270.0°

---

## Отладка

Включите логирование в `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.dahua_ptz: debug
```

В логах будет видно:
- Запускаемые CLI-команды
- Результаты выполнения
- Ошибки подключения

---

## Структура файлов

```
custom_components/dahua_ptz/
├── __init__.py          # Точка входа, сервисы
├── config_flow.py       # UI/YAML конфиг-флоу
├── const.py             # Константы
├── dahua_cli.py         # Обёртка над CLI (subprocess)
├── dahua_ptz_cli.py     # CLI-утилита (прямой вызов)
├── manifest.json        # Метаданные
└── ptz_position.json    # Трекер позиции (создаётся автоматически)
```
