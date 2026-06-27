"""Config flow for Kärcher Home Robots."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_REGION

from .karcher_api import KarcherApi, KarcherAuthError, KarcherApiError
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

REGIONS = {"eu": "Europe", "us": "USA", "cn": "China"}

STEP_SCHEMA = vol.Schema({
    vol.Required(CONF_EMAIL): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Optional(CONF_REGION, default="eu"): vol.In(REGIONS),
})


class KarcherConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            api = KarcherApi(region=user_input[CONF_REGION])
            try:
                await api.login(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
                await api.close()
            except KarcherAuthError as e:
                _LOGGER.warning("Auth error during setup: %s", e)
                errors["base"] = "invalid_auth"
            except KarcherApiError as e:
                _LOGGER.warning("API error during setup: %s", e)
                errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.exception("Unexpected error during Kärcher setup: %s", e)
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Kärcher ({user_input[CONF_EMAIL]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_SCHEMA,
            errors=errors,
        )
