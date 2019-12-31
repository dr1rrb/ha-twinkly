"""The Twinkly platform for light component"""

import logging
from typing import Any, Optional
import voluptuous as vol
from aiohttp import ClientResponseError, ClientTimeout
from homeassistant.components.light import (ATTR_BRIGHTNESS, PLATFORM_SCHEMA, SUPPORT_BRIGHTNESS, Light)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

ATTR_HOST = 'host'
ATTR_NAME = 'device_name'
HIDDEN_ATTR = (
	'code', # This is the internal status code of the API response
	'copyright', # We should not display a copyright "LEDWORKS 2018" in the Home-Assistant UI
	'mac' # Does not report the actual device mac address
)

AUTH_HEADER = 'X-Auth-Token'

EP_TIMEOUT = ClientTimeout(total=3) # It on LAN, and if too long we will get warning to the update duration in logs
EP_DEVICE_INFO = "gestalt"
EP_MODE = "led/mode"
EP_BRIGHTNESS = "led/out/brightness"
EP_LOGIN = "login"
EP_VERIFY = "verify"

CONF_HOST = 'host'
CONF_NAME = 'name'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
	{
		vol.Required(CONF_HOST): cv.string,
		vol.Optional(CONF_NAME): cv.string,
	}
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
	"""Setup callback of the platform."""
	
	session = async_get_clientsession(hass)
	async_add_entities([TwinklyLight(config.get(CONF_NAME), config[CONF_HOST], session)], True)

	return True

class TwinklyLight(Light):
	"""Implementation of the light for the Twinkly service."""

	def __init__(self, name, host, session):
		"""Initialize a TwinklyLight."""
		self._name = name
		self._host = host
		self._base_url = "http://" + host + "/xled/v1/"
		self._token = None
		self._session = session
		
		self._is_on = False
		self._brightness = 0
		self._is_available = False
		self._attributes = { ATTR_HOST: self._host }

	@property
	def supported_features(self):
		return SUPPORT_BRIGHTNESS

	@property
	def should_poll(self) -> bool:
		return True

	@property
	def available(self) -> bool:
		return self._is_available

	@property
	def name(self) -> str:
		"""Name of the device."""
		return self._name if self._name else self._attributes[ATTR_NAME] if ATTR_NAME in self._attributes else "Twinkly light"

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
			brightness = int(int(kwargs[ATTR_BRIGHTNESS])/ 2.55)
			
			# If brightness is 0, the twinkly will only "disable" the brightness,
			# which means that it will be 100%.
			if brightness == 0:
				await self.set_is_on(False)
				return
			
			await self.set_brightness(brightness)
		
		await self.set_is_on(True)
	
	async def async_turn_off(self, **kwargs) -> None:
		"""Turn device off."""
		await self.set_is_on(False)

	async def async_update(self) -> None:
		"""Asynchronously updates the device properties."""
		_LOGGER.info("Updating '%s'", self._host)

		try:
			self._is_on = await self.get_is_on()
			self._brightness = (await self.get_brigthness()) * 2.55
			
			device_info = await self.get_device_info()
			for	key,value in device_info.items():
				if key not in HIDDEN_ATTR: 
					self._attributes[key] = value

			# We don't use the echo API to track the availability since we already have to pull
			# the device to get its state.
			self._is_available = True
		except:
			# We log this as "info" as it's pretty common that the christmas ligth are not reachable
			# in jully ... it would dump way too much noise in the logs
			_LOGGER.info("Twinkly '%s' is not reachable", self._host)
			self._is_available = False
			pass

	async def set_is_on(self, is_on: bool) -> None:
		await self.send_request(EP_MODE, {'mode': "movie" if is_on else "off"})

	async def set_brightness(self, brightness: int) -> None:
		await self.send_request(EP_BRIGHTNESS, {"value":brightness, "type": "A"})

	async def get_device_info(self) -> None:
		return await self.send_request(EP_DEVICE_INFO)

	async def get_is_on(self) -> bool:
		return (await self.send_request(EP_MODE))['mode'] != "off"

	async def get_brigthness(self) -> int:
		brightness = await self.send_request(EP_BRIGHTNESS)
		return int(brightness['value']) if brightness['mode'] == "enabled" else 100

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
				raise_for_status = True,
				timeout = EP_TIMEOUT
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
			raise_for_status = True,
			timeout = EP_TIMEOUT
		)
		login_result = await login_response.json()
		_LOGGER.debug("Sucessfully logged-in to '%s'", self._host)

		# Get the token, but do not store it until it get verified
		token = login_result['authentication_token']
		
		# Verify the token is valid
		await self._session.post(
			url = self._base_url + EP_VERIFY,
			headers= {AUTH_HEADER: token},
			raise_for_status = True,
			timeout = EP_TIMEOUT
		)
		_LOGGER.debug("Sucessfully verified token to '%s'", self._host)

		self._token = token
