"""Kärcher Home Robots API client."""
from __future__ import annotations

import hashlib
import json
import random
import string
import time
from dataclasses import dataclass
from typing import Any

import aiohttp

TENANT_ID = "1528983614213726208"
PROJECT_TYPE = "android_iot.karcher"
API_VERSION = "v1"
BASE_URL_EU = "https://eu-appaiot.3irobotix.net"

# Work mode mappings from protocol docs
WORK_MODE_IDLE = {0, 35, 85, 29, 40, 14, 23}
WORK_MODE_PAUSE = {4, 31, 82, 27, 37, 9}
WORK_MODE_CLEANING = {1, 30, 81, 25, 36, 7}
WORK_MODE_GO_HOME = {5, 10, 11, 12, 21, 26, 32, 47, 38}


def _aes_key() -> bytes:
    """Derive AES key from tenantId as per protocol."""
    md5 = hashlib.md5(TENANT_ID.encode()).hexdigest()
    return md5[8:24].encode()


def _decrypt_domain(encrypted: str) -> dict:
    """Decrypt the domain JSON returned by the server."""
    try:
        from Crypto.Cipher import AES
        import base64
        key = _aes_key()
        data = base64.b64decode(encrypted)
        cipher = AES.new(key, AES.MODE_ECB)
        decrypted = cipher.decrypt(data)
        # Remove PKCS7 padding
        pad = decrypted[-1]
        decrypted = decrypted[:-pad]
        return json.loads(decrypted.decode())
    except Exception:
        return {}


def _randstr(n: int = 32) -> str:
    chars = "123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(random.choices(chars, k=n))


def _sign(user_auth: str, ts: str, nonce: str, request_data: str) -> str:
    raw = user_auth + ts + nonce + request_data
    return hashlib.md5(raw.encode()).hexdigest()


@dataclass
class KarcherDevice:
    device_id: str
    name: str
    model: str
    battery: int
    work_mode: int
    online: bool
    raw: dict

    @property
    def state(self) -> str:
        wm = self.work_mode
        if wm in WORK_MODE_CLEANING:
            return "cleaning"
        if wm in WORK_MODE_PAUSE:
            return "paused"
        if wm in WORK_MODE_GO_HOME:
            return "returning"
        return "docked"

    @property
    def is_cleaning(self) -> bool:
        return self.work_mode in WORK_MODE_CLEANING

    @property
    def is_docked(self) -> bool:
        return self.work_mode in WORK_MODE_IDLE


class KarcherApiError(Exception):
    pass


class KarcherAuthError(KarcherApiError):
    pass


class KarcherApi:
    """Async client for the Kärcher Home Robots cloud API."""

    def __init__(self, region: str = "eu") -> None:
        self._base_url = {
            "eu": BASE_URL_EU,
            "us": "https://us-appaiot.3irobotix.net",
            "cn": "https://cn-appaiot.3irobotix.net",
        }.get(region, BASE_URL_EU)
        self._user_auth: str = ""
        self._user_id: str = ""
        self._api_url: str = self._base_url
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _headers(self, request_data: str = "") -> dict:
        ts = str(int(time.time()))
        nonce = _randstr(32)
        sign = _sign(self._user_auth, ts, nonce, request_data)
        h = {
            "User-Agent": f"Android_{TENANT_ID}",
            "tenantId": TENANT_ID,
            "sign": sign,
            "ts": ts,
            "nonce": nonce,
            "Content-Type": "application/json",
        }
        if self._user_auth:
            h["authorization"] = self._user_auth
        if self._user_id:
            h["id"] = self._user_id
        return h

    async def _get(self, path: str, params: dict | None = None) -> Any:
        url = self._api_url + path
        param_str = "&".join(f"{k}={v}" for k, v in (params or {}).items())
        headers = self._headers(param_str)
        async with self._get_session().get(url, params=params, headers=headers) as resp:
            data = await resp.json(content_type=None)
        if data.get("code", 0) != 0:
            code = data.get("code")
            if code in (609, 613):
                raise KarcherAuthError(data.get("msg", "Auth error"))
            raise KarcherApiError(data.get("msg", f"API error {code}"))
        return data.get("result")

    async def _post(self, path: str, body: dict) -> Any:
        url = self._api_url + path
        body_str = json.dumps(list(body.values()), separators=(",", ":"))
        headers = self._headers(body_str)
        async with self._get_session().post(url, json=body, headers=headers) as resp:
            data = await resp.json(content_type=None)
        if data.get("code", 0) != 0:
            code = data.get("code")
            if code in (609, 613):
                raise KarcherAuthError(data.get("msg", "Auth error"))
            raise KarcherApiError(data.get("msg", f"API error {code}"))
        return data.get("result")

    async def login(self, email: str, password: str) -> None:
        """Login with email and password."""
        import hashlib
        pwd_hash = hashlib.md5(password.encode()).hexdigest()
        result = await self._post("/user-center/auth/login", {
            "tenantId": TENANT_ID,
            "lang": "en",
            "loginName": email,
            "loginPassword": pwd_hash,
            "loginType": 0,
        })
        if not result:
            raise KarcherAuthError("Login failed: no result returned")
        self._user_auth = result.get("authorization", "")
        self._user_id = result.get("userId", "")
        if not self._user_auth:
            raise KarcherAuthError("Login failed: no auth token")
        # Resolve the best API URL for this account
        await self._resolve_api_url()

    async def _resolve_api_url(self) -> None:
        try:
            result = await self._get("/network-service/domains/list", {
                "tenantId": TENANT_ID,
                "productModeCode": PROJECT_TYPE,
                "version": API_VERSION,
            })
            if result and result.get("domain"):
                domains = _decrypt_domain(result["domain"])
                if domains.get("APP_api"):
                    self._api_url = domains["APP_api"].rstrip("/")
        except Exception:
            pass  # Fall back to default

    async def get_devices(self) -> list[KarcherDevice]:
        """Fetch all devices for the logged-in user."""
        result = await self._get(
            f"/smart-home-service/smartHome/user/getDeviceInfoByUserId/{self._user_id}"
        )
        devices = []
        for item in result or []:
            props = {p["key"]: p["value"] for p in item.get("devicePropertyList", [])}
            work_mode = int(props.get("workMode", 0))
            battery = int(props.get("electricity", 0))
            device = KarcherDevice(
                device_id=item.get("deviceId", ""),
                name=item.get("deviceName", "Kärcher Robot"),
                model=item.get("modelName", "RCV5"),
                battery=battery,
                work_mode=work_mode,
                online=item.get("online", False),
                raw=item,
            )
            devices.append(device)
        return devices

    async def send_command(self, device_id: str, command: dict) -> None:
        """Send a command to a device."""
        await self._post("/smart-home-service/smartHome/device/sendCommand", {
            "deviceId": device_id,
            "tenantId": TENANT_ID,
            **command,
        })

    async def start_cleaning(self, device_id: str) -> None:
        await self.send_command(device_id, {"workMode": 1})

    async def stop_cleaning(self, device_id: str) -> None:
        await self.send_command(device_id, {"workMode": 0})

    async def pause_cleaning(self, device_id: str) -> None:
        await self.send_command(device_id, {"workMode": 4})

    async def return_to_base(self, device_id: str) -> None:
        await self.send_command(device_id, {"workMode": 5})

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
