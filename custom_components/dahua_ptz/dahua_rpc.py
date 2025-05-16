import hashlib
import aiohttp
import async_timeout
import logging
import json
from typing import Optional

_LOGGER = logging.getLogger(__name__)

class DahuaRpc:
    def __init__(self, host: str, username: str, password: str, force_text: bool = False):
        self.host = host
        self.username = username
        self.password = password
        self.force_text = force_text
        self.session: Optional[aiohttp.ClientSession] = None
        self.session_id: Optional[str] = None
        self.id = 0

    async def initialize(self):
        """Initialize the aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None
        self.session_id = None

    async def request(self, method: str, params: Optional[dict] = None, 
                     object_id: Optional[str] = None, extra: Optional[dict] = None, 
                     url: Optional[str] = None):
        """Make an async RPC request."""
        await self.initialize()
        self.id += 1
        
        data = {'method': method, 'id': self.id}
        if params is not None:
            data['params'] = params
        if object_id:
            data['object'] = object_id
        if extra is not None:
            data.update(extra)
        if self.session_id:
            data['session'] = self.session_id
        if not url:
            url = f"http://{self.host}/RPC2"
        
        try:
            async with async_timeout.timeout(10):
                async with self.session.post(
                    url,
                    json=data,
                    headers={
                        'Accept-Encoding': 'identity',
                        'Content-Type': 'application/json',
                    },
                ) as response:
                    if self.force_text:
                        text = await response.text()
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            _LOGGER.error(f"Failed to parse JSON response: {text}")
                            raise
                    else:
                        try:
                            return await response.json(content_type=None)
                        except (aiohttp.ContentTypeError, json.JSONDecodeError) as e:
                            text = await response.text()
                            _LOGGER.warning(f"Falling back to text parsing due to: {e}")
                            return json.loads(text)

        except Exception as e:
            _LOGGER.error(f"Request failed: {e}")
            await self.close()
            raise

    async def login(self):
        """Login to Dahua camera."""
        url = f'http://{self.host}/RPC2_Login'
        method = "global.login"
        params = {'userName': self.username,
                 'password': "",
                 'clientType': "Web3.0"}
        
        try:
            r = await self.request(method=method, params=params, url=url)
            self.session_id = r['session']
            realm = r['params']['realm']
            random = r['params']['random']

            pwd_phrase = f"{self.username}:{realm}:{self.password}"
            pwd_hash = hashlib.md5(pwd_phrase.encode('utf-8')).hexdigest().upper()
            pass_phrase = f"{self.username}:{random}:{pwd_hash}"
            pass_hash = hashlib.md5(pass_phrase.encode('utf-8')).hexdigest().upper()

            params = {
                'userName': self.username,
                'password': pass_hash,
                'clientType': "Web3.0",
                'authorityType': "Default",
                'passwordType': "Default"
            }
            r = await self.request(method=method, params=params, url=url)

            if not r['result']:
                raise Exception(f"Login failed: {r}")
                
        except Exception as e:
            _LOGGER.error(f"Login error: {e}")
            await self.close()
            raise

    async def ptz_control(self, action: str = "stop", code: str = "", 
                         arg1: int = 0, arg2: int = 0, arg3: int = 5):
        """Control PTZ camera."""
        method = f"ptz.{action}"
        params = {
            "code": code,
            "arg1": arg1,
            "arg2": arg2,
            "arg3": arg3,
            "arg4": 0
        }
        try:
            r = await self.request(method=method, params=params)
            if not r['result']:
                _LOGGER.warning(f"PTZ command failed: {r}")
            return r
        except Exception as e:
            _LOGGER.error(f"PTZ control error: {e}")
            await self.close()
            raise