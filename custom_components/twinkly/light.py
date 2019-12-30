"""The Twinkly platform for light component"""

import logging
from typing import Any, Optional
import voluptuous as vol
from aiohttp import ClientResponseError
from homeassistant.components.light import (ATTR_BRIGHTNESS, PLATFORM_SCHEMA, SUPPORT_BRIGHTNESS, Light)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

ATTR_HOST = 'host'
HIDDEN_ATTR = (
	'device_name', # Normalized in the name property
	'code', # This is the internal status code of the API response
	'copyright', # We should not display a copyright "LEDWORKS 2018" in the Home-Assistant UI
	'mac' # Does not report the actual device mac address
)

AUTH_HEADER = 'X-Auth-Token'

EP_DEVICE_INFO = "gestalt"
EP_MODE = "led/mode"
EP_BRIGHTNESS = "led/out/brightness"
EP_LOGIN = "login"
EP_VERIFY = "verify"

CONF_HOST = 'host'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
    }
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
	"""Setup callback of the platform."""
	
	session = async_get_clientsession(hass)
	async_add_entities([TwinklyLight(session, config[CONF_HOST])], True)

	return True

class TwinklyLight(Light):
	"""Implementation of the light for the Twinkly service."""

	def __init__(self, session, host):
		"""Initialize a TwinklyLight."""
		self._name = 'Twinkly light'
		self._is_on = False
		self._brightness = 0

		self._session = session
		self._host = host
		self._base_url = "http://" + host + "/xled/v1/"
		self._token = None
		self._attributes = { ATTR_HOST: self._host }

	@property
	def supported_features(self):
		return SUPPORT_BRIGHTNESS

	@property
	def should_poll(self) -> bool:
		return True

	@property
	def available(self) -> bool:
		return True

	@property
	def name(self) -> str:
		"""Name of the device."""
		return self._name

	@property
	def is_on(self) -> bool:
		"""Return true if light is on."""
		return self._is_on

	@property
	def brightness(self) -> Optional[int]:
		"""Return the brightness of the light."""
		return self._brightness

	@property
	def state_attributes(self) -> dict:
		"""Return device specific state attributes."""
		
		attributes = self._attributes
		
		# Make sure to update any normalized property
		attributes[ATTR_HOST] = self._host
		attributes[ATTR_BRIGHTNESS] = self._brightness

		return attributes

	async def async_turn_on(self, **kwargs) -> None:
		"""Turn device on."""
		if ATTR_BRIGHTNESS in kwargs:
			await self.set_brightness(kwargs[ATTR_BRIGHTNESS])
		
		await self.set_is_on(True)
	
	async def async_turn_off(self, **kwargs) -> None:
		"""Turn device off."""
		await self.set_is_on(False)

	async def async_update(self) -> None:
		"""Asynchronously updates the device properties."""
		_LOGGER.info("Updating '%s'", self._host)
		self._is_on = await self.get_is_on()
		self._brightness = await self.get_brigthness()
		
		device_info = await self.get_device_info()
		self._name = device_info['device_name']
		for	key,value in device_info.items():
			if key not in HIDDEN_ATTR: 
				self._attributes[key] = value

	async def set_is_on(self, is_on: bool) -> None:
		await self.send_request(EP_MODE, {'mode': "movie" if is_on else "off"})

	async def set_brightness(self, brightness) -> None:
		await self.send_request(EP_BRIGHTNESS, {"value":int(int(brightness) / 2.55), "type": "A"})

	async def get_device_info(self) -> None:
		return await self.send_request(EP_DEVICE_INFO)

	async def get_is_on(self) -> bool:
		return (await self.send_request(EP_MODE))['mode'] != "off"

	async def get_brigthness(self) -> int:
		brightness = await self.send_request(EP_BRIGHTNESS)
		return int(int(brightness['value']) * 2.55) if brightness['mode'] == "enabled" else 255

	async def send_request(self, endpoint: str, data: Any=None, retry: int=1) -> Any:
		"""Send an authenticated request with auto retry if not yet auth."""
		if self._token is None:
			await self.auth()

		try:
			response = await self._session.request(
				method = "GET" if data is None else "POST",
				url = self._base_url + endpoint,
				json = data,
				headers = {AUTH_HEADER: self._token},
				raise_for_status = True
			)
			result = await response.json() if data is None else None
			return result
		except ClientResponseError as err:
			if err.code == 401 and retry > 0:
				self._token = None
				return await self.send_request(endpoint, data, retry - 1)
			raise

	async def auth(self) -> None:
		"""Authenticates to the device."""
		_LOGGER.info("Authenticating to '%s'", self._host)
		
		# Login to the device using a hard-coded challenge
		login_response = await self._session.post(
			url = self._base_url + EP_LOGIN, 
			json = {"challenge":"Uswkc0TgJDmwl5jrsyaYSwY8fqeLJ1ihBLAwYcuADEo="},
			raise_for_status = True)
		login_result = await login_response.json()
		_LOGGER.debug("Sucessfully logged-in to '%s'", self._host)

		# Get the token, but do not store it until it get verified
		token = login_result['authentication_token']
		
		# Verify the token is valid
		await self._session.post(
			url = self._base_url + EP_VERIFY,
			headers= {AUTH_HEADER: token},
			raise_for_status = True
		)
		_LOGGER.debug("Sucessfully verified token to '%s'", self._host)

		self._token = token
