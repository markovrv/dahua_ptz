"""Интеграция Dahua PTZ для Home Assistant.

Управляет камерой через dahua_ptz_cli.py (subprocess).
"""

import logging
import os
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN, SERVICE_RESTART, SERVICE_PTZ_CONTROL,
    SERVICE_MOVE_RELATIVE, SERVICE_MOVE_ABSOLUTE, SERVICE_GO_HOME,
    CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_SCRIPT_PATH,
    DEFAULT_SCRIPT_PATH, DEFAULT_SPEED,
)
from .dahua_cli import DahuaCli

_LOGGER = logging.getLogger(__name__)

PLATFORMS = []


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Настройка из configuration.yaml (опционально)."""
    if DOMAIN not in config:
        return True

    # Если уже есть config entries, игнорируем YAML
    if hass.config_entries.async_entries(DOMAIN):
        return True

    # Создаём config entry из YAML
    conf = config[DOMAIN]
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "import"},
            data=conf,
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Настройка из config entry."""
    hass.data.setdefault(DOMAIN, {})

    cli = await _init_connection(hass, entry)
    if cli is None:
        raise ConfigEntryNotReady

    hass.data[DOMAIN]["client"] = cli

    await _register_services(hass)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    _LOGGER.info("Dahua PTZ инициализирован: %s", entry.data[CONF_HOST])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Выгрузка config entry."""
    hass.data[DOMAIN].pop("client", None)
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Обновление опций."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _init_connection(hass: HomeAssistant, entry: ConfigEntry):
    """Инициализация подключения."""
    config = entry.data
    speed = entry.options.get("speed", DEFAULT_SPEED)
    script_path = entry.options.get(
        CONF_SCRIPT_PATH, config.get(CONF_SCRIPT_PATH, DEFAULT_SCRIPT_PATH)
    )

    cli = DahuaCli(
        host=config[CONF_HOST],
        username=config[CONF_USERNAME],
        password=config[CONF_PASSWORD],
        script_path=script_path,
        speed=speed,
    )

    # Проверяем подключение
    status = hass.async_add_executor_job(cli.status)
    status_result = await status
    if status_result is None:
        _LOGGER.error("Не удалось подключиться к камере: %s", config[CONF_HOST])
        _LOGGER.error("CLI-скрипт: %s (существует: %s)", cli.script_path, os.path.isfile(cli.script_path))
        return None

    _LOGGER.info("Подключение к камере успешно: %s", status_result)
    return cli


async def _register_services(hass: HomeAssistant) -> None:
    """Регистрация сервисов."""

    async def async_handle_ptz_control(call: ServiceCall):
        action = call.data.get("action", "stop")
        code = call.data.get("code", "")
        arg1 = call.data.get("arg1", 0)
        arg2 = call.data.get("arg2", 0)

        cli = hass.data[DOMAIN].get("client")
        if not cli:
            _LOGGER.error("Клиент Dahua не инициализирован")
            return

        if code == "PositionABS":
            await hass.async_add_executor_job(cli.move_absolute, arg1 / 10, arg2 / 10)
        elif code == "Stop":
            _LOGGER.info("PTZ stop (не требуется для PositionABS)")
        else:
            _LOGGER.warning("ptz_control: код '%s' не поддерживается, используйте move_relative", code)

    async def async_handle_move_relative(call: ServiceCall):
        direction = call.data.get("direction")
        degrees = call.data.get("degrees")

        cli = hass.data[DOMAIN].get("client")
        if not cli:
            _LOGGER.error("Клиент Dahua не инициализирован")
            return

        commands = {
            "left": cli.move_left,
            "right": cli.move_right,
            "up": cli.move_up,
            "down": cli.move_down,
        }

        func = commands.get(direction)
        if func:
            await hass.async_add_executor_job(func, degrees)
        else:
            _LOGGER.error("Неизвестное направление: %s", direction)

    async def async_handle_move_absolute(call: ServiceCall):
        pan = call.data.get("pan")
        tilt = call.data.get("tilt")

        cli = hass.data[DOMAIN].get("client")
        if not cli:
            _LOGGER.error("Клиент Dahua не инициализирован")
            return

        await hass.async_add_executor_job(cli.move_absolute, pan, tilt)

    async def async_handle_go_home(call: ServiceCall):
        cli = hass.data[DOMAIN].get("client")
        if not cli:
            _LOGGER.error("Клиент Dahua не инициализирован")
            return

        await hass.async_add_executor_job(cli.go_home)

    async def async_handle_restart(call: ServiceCall):
        _LOGGER.info("Перезагрузка интеграции Dahua PTZ")
        entry = next(iter(hass.config_entries.async_entries(DOMAIN)), None)
        if entry:
            await hass.config_entries.async_reload(entry.entry_id)

    hass.services.async_register(
        DOMAIN, SERVICE_PTZ_CONTROL, async_handle_ptz_control,
        schema=vol.Schema({
            vol.Optional("action"): vol.In(["start", "stop"]),
            vol.Optional("code"): cv.string,
            vol.Optional("arg1"): vol.Any(int, float),
            vol.Optional("arg2"): vol.Any(int, float),
            vol.Optional("arg3"): vol.Any(int, float),
        })
    )

    hass.services.async_register(
        DOMAIN, SERVICE_MOVE_RELATIVE, async_handle_move_relative,
        schema=vol.Schema({
            vol.Required("direction"): vol.In(["left", "right", "up", "down"]),
            vol.Required("degrees"): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=360)),
        })
    )

    hass.services.async_register(
        DOMAIN, SERVICE_MOVE_ABSOLUTE, async_handle_move_absolute,
        schema=vol.Schema({
            vol.Required("pan"): vol.All(vol.Coerce(float), vol.Range(min=0, max=360)),
            vol.Required("tilt"): vol.All(vol.Coerce(float), vol.Range(min=-90, max=90)),
        })
    )

    hass.services.async_register(
        DOMAIN, SERVICE_GO_HOME, async_handle_go_home
    )

    hass.services.async_register(
        DOMAIN, SERVICE_RESTART, async_handle_restart
    )
