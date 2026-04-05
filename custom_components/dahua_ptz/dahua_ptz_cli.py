"""
Утилита командной строки для управления PTZ камерой Dahua.

Все команды работают через PositionABS (абсолютное позиционирование).
Скрипт запоминает последнюю известную позицию и рассчитывает новую.

Примеры:
  python dahua_ptz_cli.py left 90          # Повернуть на 90° влево
  python dahua_ptz_cli.py right 45         # Повернуть на 45° вправо
  python dahua_ptz_cli.py up 30            # Наклонить на 30° вверх
  python dahua_ptz_cli.py down 15          # Наклонить на 15° вниз
  python dahua_ptz_cli.py absolute 180 45  # Перейти к Pan=180°, Tilt=45°
  python dahua_ptz_cli.py status           # Показать позицию
  python dahua_ptz_cli.py home             # Домашняя позиция
"""

import hashlib
import json
import sys
import time
import os
import argparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# ─── Настройки подключения ───────────────────────────────────────────────
HOST = "192.168.1.114"
USERNAME = "admin"
PASSWORD = "L2E3C8C0"
POSITION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ptz_position.json")
# ──────────────────────────────────────────────────────────────────────────


class DahuaPTZ:
    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username
        self.password = password
        self.session_id = None
        self.request_id = 0
        self.base_url = f"http://{host}/RPC2"
        self.login_url = f"http://{host}/RPC2_Login"

    def _make_request(self, method: str, params: dict, url: str = None) -> dict:
        self.request_id += 1
        if url is None:
            url = self.base_url

        data = {
            "method": method,
            "id": self.request_id,
            "params": params
        }
        if self.session_id:
            data["session"] = self.session_id

        body = json.dumps(data).encode("utf-8")
        req = Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept-Encoding": "identity"
            },
            method="POST"
        )

        with urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)

    def login(self) -> bool:
        params = {
            "userName": self.username,
            "password": "",
            "clientType": "Web3.0"
        }
        resp = self._make_request("global.login", params, url=self.login_url)
        self.session_id = resp.get("session")
        realm = resp["params"]["realm"]
        random_val = resp["params"]["random"]

        pwd_phrase = f"{self.username}:{realm}:{self.password}"
        pwd_hash = hashlib.md5(pwd_phrase.encode("utf-8")).hexdigest().upper()
        pass_phrase = f"{self.username}:{random_val}:{pwd_hash}"
        pass_hash = hashlib.md5(pass_phrase.encode("utf-8")).hexdigest().upper()

        params = {
            "userName": self.username,
            "password": pass_hash,
            "clientType": "Web3.0",
            "authorityType": "Default",
            "passwordType": "Default"
        }
        resp = self._make_request("global.login", params, url=self.login_url)

        if resp.get("result") is True:
            self.session_id = resp.get("session", self.session_id)
            return True
        return False

    def ptz_absolute(self, pan: int, tilt: int, zoom: int = 0, speed: int = 5) -> bool:
        """Переход к абсолютной позиции."""
        params = {
            "code": "PositionABS",
            "arg1": pan,
            "arg2": tilt,
            "arg3": zoom,
            "arg4": 0
        }
        resp = self._make_request("ptz.start", params)
        return resp.get("result", False)

    def ptz_stop(self) -> bool:
        params = {
            "code": "Stop",
            "arg1": 0,
            "arg2": 0,
            "arg3": 0,
            "arg4": 0
        }
        resp = self._make_request("ptz.stop", params)
        return resp.get("result", False)

    def logout(self):
        try:
            self._make_request("global.logout", {}, url=self.login_url)
        except:
            pass


class PositionTracker:
    """Отслеживает позицию PTZ через локальный файл."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.pan = 0
        self.tilt = 0
        self.zoom = 0
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    self.pan = data.get("pan", 0)
                    self.tilt = data.get("tilt", 0)
                    self.zoom = data.get("zoom", 0)
            except:
                pass

    def save(self):
        with open(self.filepath, "w") as f:
            json.dump({
                "pan": self.pan,
                "tilt": self.tilt,
                "zoom": self.zoom
            }, f, indent=2)

    def set_position(self, pan: int, tilt: int, zoom: int = 0):
        self.pan = pan
        self.tilt = tilt
        self.zoom = zoom
        self.save()

    def move_by(self, pan_delta: int = 0, tilt_delta: int = 0, zoom_delta: int = 0):
        """Сдвинуть на относительное значение и сохранить."""
        self.pan += pan_delta
        self.tilt += tilt_delta
        self.zoom += zoom_delta

        # Нормализация Pan (0-3600 = 0-360°)
        while self.pan < 0:
            self.pan += 3600
        while self.pan >= 3600:
            self.pan -= 3600

        self.save()


def main():
    parser = argparse.ArgumentParser(
        description="Управление PTZ камерой Dahua (через PositionABS)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  %(prog)s left 90          Повернуть на 90° влево
  %(prog)s right 45         Повернуть на 45° вправо
  %(prog)s up 30            Наклонить на 30° вверх
  %(prog)s down 15          Наклонить на 15° вниз
  %(prog)s absolute 180 45  Перейти к Pan=180°, Tilt=45°
  %(prog)s status           Показать позицию
  %(prog)s home             Домашняя позиция (0, 0)
  %(prog)s reset            Сбросить позицию (0, 0)
        """
    )

    parser.add_argument(
        "command",
        choices=["left", "right", "up", "down", "absolute", "status", "home", "reset"],
        help="Команда управления"
    )
    parser.add_argument("value", nargs="*", type=float, default=[])
    parser.add_argument("--speed", "-s", type=int, default=5, choices=range(1, 11))
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--user", default=USERNAME)
    parser.add_argument("--password", default=PASSWORD)

    args = parser.parse_args()

    # Валидация
    if args.command == "absolute":
        if len(args.value) < 2:
            parser.error("Команда 'absolute' требует 2 значения: pan tilt")
    elif args.command in ("left", "right", "up", "down"):
        if len(args.value) != 1:
            parser.error(f"Команда '{args.command}' требует угол в градусах")

    # Трекер позиции
    tracker = PositionTracker(POSITION_FILE)

    camera = DahuaPTZ(args.host, args.user, args.password)
    if not camera.login():
        print("❌ Ошибка авторизации")
        sys.exit(1)

    try:
        command = args.command

        if command == "status":
            pan_deg = tracker.pan / 10
            tilt_deg = tracker.tilt / 10
            print(f"📍 Позиция: Pan={pan_deg:.1f}° ({tracker.pan}), Tilt={tilt_deg:.1f}° ({tracker.tilt}), Zoom={tracker.zoom}")

        elif command == "reset":
            tracker.set_position(0, 0, 0)
            print("📍 Позиция сброшена: Pan=0°, Tilt=0°")

        elif command == "left":
            degrees = args.value[0]
            units = int(degrees * 10)
            tracker.move_by(pan_delta=-units)
            print(f"🔄 Влево на {degrees}° → Pan={tracker.pan / 10:.1f}°")
            if camera.ptz_absolute(tracker.pan, tracker.tilt, tracker.zoom, args.speed):
                print("✓ Выполнено")
            else:
                print("❌ Ошибка")

        elif command == "right":
            degrees = args.value[0]
            units = int(degrees * 10)
            tracker.move_by(pan_delta=units)
            print(f"🔄 Вправо на {degrees}° → Pan={tracker.pan / 10:.1f}°")
            if camera.ptz_absolute(tracker.pan, tracker.tilt, tracker.zoom, args.speed):
                print("✓ Выполнено")
            else:
                print("❌ Ошибка")

        elif command == "up":
            degrees = args.value[0]
            units = int(degrees * 10)
            tracker.move_by(tilt_delta=units)
            print(f"📈 Вверх на {degrees}° → Tilt={tracker.tilt / 10:.1f}°")
            if camera.ptz_absolute(tracker.pan, tracker.tilt, tracker.zoom, args.speed):
                print("✓ Выполнено")
            else:
                print("❌ Ошибка")

        elif command == "down":
            degrees = args.value[0]
            units = int(degrees * 10)
            tracker.move_by(tilt_delta=-units)
            print(f"📉 Вниз на {degrees}° → Tilt={tracker.tilt / 10:.1f}°")
            if camera.ptz_absolute(tracker.pan, tracker.tilt, tracker.zoom, args.speed):
                print("✓ Выполнено")
            else:
                print("❌ Ошибка")

        elif command == "absolute":
            pan = args.value[0]
            tilt = args.value[1]
            pan_units = int(pan * 10)
            tilt_units = int(tilt * 10)
            tracker.set_position(pan_units, tilt_units)
            print(f"🎯 Позиция: Pan={pan}°, Tilt={tilt}°")
            if camera.ptz_absolute(pan_units, tilt_units, 0, args.speed):
                print("✓ Выполнено")
            else:
                print("❌ Ошибка")

        elif command == "home":
            tracker.set_position(0, 0, 0)
            print("🏠 Домашняя позиция: Pan=0°, Tilt=0°")
            if camera.ptz_absolute(0, 0, 0, args.speed):
                print("✓ Выполнено")
            else:
                print("❌ Ошибка")

    finally:
        camera.logout()


if __name__ == "__main__":
    main()
