import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

from .dahua_rpc import DahuaRpc
from .const import DOMAIN, SERVICE_RESTART, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_FORCE_TEXT

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    vol.Optional(DOMAIN): vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_FORCE_TEXT, default=False): cv.boolean,
    })
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Dahua PTZ component from configuration.yaml."""
    if DOMAIN not in config:
        return True

    # Check if already configured
    if hass.config_entries.async_entries(DOMAIN):
        _LOGGER.warning("Config entry already exists, ignoring YAML configuration")
        return True

    # Create config entry from YAML
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=config[DOMAIN],
        )
    )
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dahua PTZ from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Initialize connection
    if not await _init_connection(hass, entry):
        raise ConfigEntryNotReady

    # Register services
    await _register_services(hass)

    # Add update listener for config entry changes
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if dahua := hass.data[DOMAIN].get("client"):
        await dahua.close()
    
    hass.data[DOMAIN].pop("client", None)
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
        hass.data[DOMAIN]["client"] = dahua
        return True
    except Exception as e:
        _LOGGER.error(f"Failed to connect to Dahua camera: {e}")
        return False

async def _register_services(hass: HomeAssistant) -> None:
    """Register services for Dahua PTZ."""
    async def async_handle_ptz_control(call):
        """Handle PTZ control service calls."""
        if "client" not in hass.data[DOMAIN]:
            _LOGGER.error("Dahua client not initialized")
            return

        dahua = hass.data[DOMAIN]["client"]
        action = call.data.get("action", "stop")
        code = call.data.get("code", "")
        arg1 = call.data.get("arg1", 0)
        arg2 = call.data.get("arg2", 0)
        arg3 = call.data.get("arg3", 5)
        
        await dahua.ptz_control(action, code, arg1, arg2, arg3)

    async def async_handle_restart(call):
        """Handle restart service call."""
        _LOGGER.info("Restarting Dahua PTZ integration")
        entry = next(iter(hass.config_entries.async_entries(DOMAIN)), None)
        if entry:
            await async_reload_entry(hass, entry)

    hass.services.async_register(
        DOMAIN, "ptz_control", async_handle_ptz_control,
        schema=vol.Schema({
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
        """Close the session when HA stops."""
        if "client" in hass.data[DOMAIN]:
            await hass.data[DOMAIN]["client"].close()

    hass.bus.async_listen_once("homeassistant_stop", async_close)