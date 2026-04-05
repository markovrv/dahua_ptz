"""Config flow для интеграции Dahua PTZ."""

from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol

from .const import (
    DOMAIN, CONF_HOST, CONF_USERNAME, CONF_PASSWORD,
    CONF_SCRIPT_PATH, DEFAULT_SCRIPT_PATH,
)


class DahuaPTZConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Обработка config flow для Dahua PTZ."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Начальный шаг."""
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_HOST],
                data=user_input,
            )

        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(CONF_SCRIPT_PATH, default=DEFAULT_SCRIPT_PATH): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_import(self, import_config=None):
        """Импорт из YAML."""
        if import_config is None:
            return self.async_abort(reason="no_config")

        await self.async_set_unique_id(import_config[CONF_HOST])
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=import_config[CONF_HOST],
            data={
                CONF_HOST: import_config[CONF_HOST],
                CONF_USERNAME: import_config[CONF_USERNAME],
                CONF_PASSWORD: import_config[CONF_PASSWORD],
                CONF_SCRIPT_PATH: import_config.get(CONF_SCRIPT_PATH, DEFAULT_SCRIPT_PATH),
            },
        )
