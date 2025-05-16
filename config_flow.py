from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
from .const import DOMAIN, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_FORCE_TEXT

class DahuaPTZConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dahua PTZ."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
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
            vol.Optional(CONF_FORCE_TEXT, default=False): bool,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_import(self, import_config=None):
        """Handle import from YAML."""
        # Set unique ID from host
        await self.async_set_unique_id(import_config[CONF_HOST])
        self._abort_if_unique_id_configured()
        
        return self.async_create_entry(
            title=import_config[CONF_HOST],
            data={
                CONF_HOST: import_config[CONF_HOST],
                CONF_USERNAME: import_config[CONF_USERNAME],
                CONF_PASSWORD: import_config[CONF_PASSWORD],
                CONF_FORCE_TEXT: import_config.get(CONF_FORCE_TEXT, False),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return DahuaPTZOptionsFlowHandler(config_entry)

class DahuaPTZOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Dahua PTZ."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_FORCE_TEXT,
                    default=self.config_entry.options.get(CONF_FORCE_TEXT, False),
                ): bool,
            }),
        )