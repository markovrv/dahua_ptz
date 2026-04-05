"""Обёртка над dahua_ptz_cli.py для использования в Home Assistant."""

import json
import logging
import os
import subprocess
from typing import Optional

_LOGGER = logging.getLogger(__name__)


class DahuaCli:
    """Управление камерой Dahua через CLI-скрипт."""

    def __init__(self, host: str, username: str, password: str,
                 script_path: str = "", speed: int = 5):
        self.host = host
        self.username = username
        self.password = password
        self.speed = speed

        # Если скрипт не найден по указанному пути — ищем рядом с dahua_cli.py
        auto_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "dahua_ptz_cli.py"
        )

        if script_path and os.path.isfile(os.path.abspath(script_path)):
            self.script_path = os.path.abspath(script_path)
        elif os.path.isfile(auto_path):
            self.script_path = auto_path
        elif script_path:
            # Пользователь указал путь, но файл не существует — используем его
            # для корректной ошибки
            self.script_path = os.path.abspath(script_path)
        else:
            self.script_path = auto_path

    def _run(self, args: list) -> Optional[dict]:
        """Выполнить CLI-команду и вернуть результат."""
        cmd = [
            "python", self.script_path,
            *args,
            "--host", self.host,
            "--user", self.username,
            "--password", self.password,
        ]

        _LOGGER.debug("Запуск CLI: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )

            output = {
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "success": result.returncode == 0
            }

            if result.stderr:
                _LOGGER.warning("CLI stderr: %s", result.stderr)

            return output

        except subprocess.TimeoutExpired:
            _LOGGER.error("Таймаут CLI-команды: %s", " ".join(cmd))
            return None
        except Exception as e:
            _LOGGER.error("Ошибка выполнения CLI: %s", e)
            return None

    def status(self) -> Optional[dict]:
        """Получить текущую позицию."""
        result = self._run(["status"])
        if result and result["success"]:
            # Парсим вывод: "📍 Позиция: Pan=0.0° (0), Tilt=0.0° (0), Zoom=0"
            return self._parse_status(result["stdout"])
        return None

    def move_left(self, degrees: float) -> Optional[dict]:
        """Повернуть влево."""
        return self._run(["left", str(degrees), "--speed", str(self.speed)])

    def move_right(self, degrees: float) -> Optional[dict]:
        """Повернуть вправо."""
        return self._run(["right", str(degrees), "--speed", str(self.speed)])

    def move_up(self, degrees: float) -> Optional[dict]:
        """Наклонить вверх."""
        return self._run(["up", str(degrees), "--speed", str(self.speed)])

    def move_down(self, degrees: float) -> Optional[dict]:
        """Наклонить вниз."""
        return self._run(["down", str(degrees), "--speed", str(self.speed)])

    def move_absolute(self, pan: float, tilt: float) -> Optional[dict]:
        """Перейти к абсолютной позиции."""
        return self._run([
            "absolute", str(pan), str(tilt),
            "--speed", str(self.speed)
        ])

    def go_home(self) -> Optional[dict]:
        """Вернуться в домашнюю позицию."""
        return self._run(["home", "--speed", str(self.speed)])

    def reset_position(self) -> Optional[dict]:
        """Сбросить трекер позиции."""
        return self._run(["reset"])

    @staticmethod
    def _parse_status(text: str) -> dict:
        """Парсинг вывода статуса."""
        # "📍 Позиция: Pan=0.0° (0), Tilt=0.0° (0), Zoom=0"
        status = {"pan": 0, "tilt": 0, "zoom": 0, "raw": text}
        try:
            if "Pan=" in text:
                pan_part = text.split("Pan=")[1]
                status["pan"] = float(pan_part.split("°")[0])
            if "Tilt=" in text:
                tilt_part = text.split("Tilt=")[1]
                status["tilt"] = float(tilt_part.split("°")[0])
            if "Zoom=" in text:
                zoom_part = text.split("Zoom=")[1]
                status["zoom"] = int(zoom_part.split()[0].rstrip(","))
        except (ValueError, IndexError) as e:
            _LOGGER.warning("Не удалось распарсить статус '%s': %s", text, e)
        return status
