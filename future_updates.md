# The code to support multiple Dahua PTZ cameras 
Here are the key changes needed:

1. First, let's update `const.py` to add a new constant for storing camera instances:

```python
"""Constants for Dahua PTZ integration."""
DOMAIN = "dahua_ptz"

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_FORCE_TEXT = "force_text"
CONF_NAME = "name"  # Added for friendly names

SERVICE_RESTART = "restart"
SERVICE_PTZ_CONTROL = "ptz_control"

DATA_CLIENTS = "clients"  # Key for storing multiple camera clients
```

2. Update `config_flow.py` to include a friendly name field:

```python
from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
from .const import DOMAIN, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_FORCE_TEXT, CONF_NAME

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
                title=user_input.get(CONF_NAME, user_input[CONF_HOST]),
                data=user_input,
            )

        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(CONF_NAME): str,
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
            title=import_config.get(CONF_NAME, import_config[CONF_HOST]),
            data={
                CONF_HOST: import_config[CONF_HOST],
                CONF_USERNAME: import_config[CONF_USERNAME],
                CONF_PASSWORD: import_config[CONF_PASSWORD],
                CONF_FORCE_TEXT: import_config.get(CONF_FORCE_TEXT, False),
                CONF_NAME: import_config.get(CONF_NAME, import_config[CONF_HOST]),
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
```

3. Update `__init__.py` to handle multiple cameras:

```python
import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

from .dahua_rpc import DahuaRpc
from .const import DOMAIN, SERVICE_RESTART, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_FORCE_TEXT, DATA_CLIENTS

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    vol.Optional(DOMAIN): vol.All(cv.ensure_list, [{
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_FORCE_TEXT, default=False): cv.boolean,
    }])
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Dahua PTZ component from configuration.yaml."""
    if DOMAIN not in config:
        return True

    # Check if already configured
    if hass.config_entries.async_entries(DOMAIN):
        _LOGGER.warning("Config entries already exist, ignoring YAML configuration")
        return True

    # Create config entries from YAML
    for camera_config in config[DOMAIN]:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data=camera_config,
            )
        )
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dahua PTZ from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(DATA_CLIENTS, {})

    # Initialize connection
    if not await _init_connection(hass, entry):
        raise ConfigEntryNotReady

    # Register services if not already registered
    if len(hass.data[DOMAIN][DATA_CLIENTS]) == 1:
        await _register_services(hass)

    # Add update listener for config entry changes
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.entry_id in hass.data[DOMAIN].get(DATA_CLIENTS, {}):
        dahua = hass.data[DOMAIN][DATA_CLIENTS][entry.entry_id]
        await dahua.close()
        hass.data[DOMAIN][DATA_CLIENTS].pop(entry.entry_id)
    
    # Unregister services if no cameras left
    if not hass.data[DOMAIN].get(DATA_CLIENTS):
        hass.services.async_remove(DOMAIN, SERVICE_RESTART)
        hass.services.async_remove(DOMAIN, "ptz_control")
    
    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

async def _init_connection(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialize connection to Dahua camera."""
    config = entry.data
    force_text = entry.options.get(CONF_FORCE_TEXT, False)

    dahua = DahuaRpc(
        host=config[CONF_HOST],
        username=config[CONF_USERNAME],
        password=config[CONF_PASSWORD],
        force_text=force_text
    )

    try:
        await dahua.login()
        hass.data[DOMAIN][DATA_CLIENTS][entry.entry_id] = dahua
        return True
    except Exception as e:
        _LOGGER.error(f"Failed to connect to Dahua camera {config[CONF_HOST]}: {e}")
        return False

async def _register_services(hass: HomeAssistant) -> None:
    """Register services for Dahua PTZ."""
    async def async_handle_ptz_control(call):
        """Handle PTZ control service calls."""
        if not hass.data[DOMAIN].get(DATA_CLIENTS):
            _LOGGER.error("No Dahua clients initialized")
            return

        camera_id = call.data.get("camera_id")
        if camera_id:
            if camera_id not in hass.data[DOMAIN][DATA_CLIENTS]:
                _LOGGER.error(f"Camera ID {camera_id} not found")
                return
            dahua = hass.data[DOMAIN][DATA_CLIENTS][camera_id]
        else:
            # If no camera_id specified, use the first one
            dahua = next(iter(hass.data[DOMAIN][DATA_CLIENTS.values()), None)
            if not dahua:
                _LOGGER.error("No Dahua clients available")
                return

        action = call.data.get("action", "stop")
        code = call.data.get("code", "")
        arg1 = call.data.get("arg1", 0)
        arg2 = call.data.get("arg2", 0)
        arg3 = call.data.get("arg3", 5)
        
        await dahua.ptz_control(action, code, arg1, arg2, arg3)

    async def async_handle_restart(call):
        """Handle restart service call."""
        _LOGGER.info("Restarting all Dahua PTZ integrations")
        for entry_id in list(hass.data[DOMAIN].get(DATA_CLIENTS, {}).keys()):
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry:
                await async_reload_entry(hass, entry)

    hass.services.async_register(
        DOMAIN, "ptz_control", async_handle_ptz_control,
        schema=vol.Schema({
            vol.Optional("camera_id"): str,
            vol.Optional("action"): vol.In(["start", "stop"]),
            vol.Optional("code"): cv.string,
            vol.Optional("arg1"): vol.Any(int, float),
            vol.Optional("arg2"): vol.Any(int, float),
            vol.Optional("arg3"): vol.Any(int, float),
        })
    )

    hass.services.async_register(
        DOMAIN, SERVICE_RESTART, async_handle_restart
    )

    async def async_close(event):
        """Close all sessions when HA stops."""
        for dahua in hass.data[DOMAIN].get(DATA_CLIENTS, {}).values():
            await dahua.close()

    hass.bus.async_listen_once("homeassistant_stop", async_close)
```

4. Update `manifest.json` to bump the version:

```json
{
  "domain": "dahua_ptz",
  "name": "Dahua PTZ Camera Control",
  "documentation": "https://github.com/markovrv/dahua_ptz",
  "requirements": ["aiohttp>=3.7.4", "async_timeout>=3.0.1"],
  "dependencies": [],
  "codeowners": ["@markovrv"],
  "version": "1.1.0",
  "iot_class": "local_polling",
  "config_flow": true
}
```

Key changes made:
1. Added support for multiple camera instances in the configuration
2. Each camera is now stored with its config entry ID as the key
3. Added a `camera_id` parameter to the PTZ control service to specify which camera to control
4. Services are now only registered once (when the first camera is added) and unregistered when the last camera is removed
5. Added support for friendly names for each camera
6. Updated the YAML configuration schema to support a list of cameras
7. Improved error handling and logging for multiple cameras

The `dahua_rpc.py` file doesn't need any changes as it already supports individual camera connections.

Now users can:
1. Add multiple cameras through the UI or YAML
2. Control specific cameras using the `camera_id` parameter in service calls
3. Have friendly names for each camera
4. Restart all integrations at once or manage them individually