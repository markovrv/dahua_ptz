"""Константы для интеграции Dahua PTZ."""
DOMAIN = "dahua_ptz"

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCRIPT_PATH = "script_path"

SERVICE_RESTART = "restart"
SERVICE_PTZ_CONTROL = "ptz_control"
SERVICE_MOVE_RELATIVE = "move_relative"
SERVICE_MOVE_ABSOLUTE = "move_absolute"
SERVICE_GO_HOME = "go_home"

DEFAULT_SCRIPT_PATH = "dahua_ptz_cli.py"
DEFAULT_SPEED = 5
