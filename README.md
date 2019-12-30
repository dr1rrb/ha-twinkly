# Twinkly for Home-Assistant

This projects lets you control your [twinkly christmas lights](https://twinkly.com/) 
from [Home-Assistant](https://www.home-assistant.io/)

Using this component you are able to:
- Turn lights on and off 
- Configure the brigthness

![integration example](./assets/integration.png "Integration example")

## Setup
### Installation using HACS (recommended)

_Learn more [about HACS](https://hacs.xyz/)_

This integration is not yet listed in the default repositories of HACS, you have to configure it manually:
1. Go to the HACS in your Home-Assistant installation
1. At the top of the HACS screen, select **settings**
1. Add a custom repo `dr1rrb/ha-twinkly` as `integration` (don't forget to click save)
1. In the **integrations** tab, you can now search and install "Twinkly"

_Continue to [configuration](#configuration)_

### Manual install
1. From the root directory of your HA, create a directory `custom_components/twinkly`
1. Download all files from the [`custom_components/twinkly` directory](./custom_components/twinkly) of this repo and copy them in the folder you just created

_Continue to [configuration](#configuration)_

### Configuration
1. In you `configuration.yaml`, in the `light` section add your twinkly device:
```yaml
light:
  - platform: twinkly
    host: 192.168.123.123
    name: Christmas tree 
```

- **Host:** [Required] We currently do not support floating IP address, so make sure to assign a static IP to your twkinly device.
  You can configure it in your router.
- **Name:** [Optional] Defines the name of this device. Even if it's optional, **we higly recommend you to configure it**. 
  If not set, the name will be retreived from the device, which means that if the device is not available (in jully for instance ;)), 
  it will fallback to the default name which is 'Twinkly light' (and the device ID will be updated accordingly by HA).

#### Name


## FAQ
### Is it possible to change the effect from HA?
Unfortunately, when you change the effect from the Twinkly app, it actually re-write the full light effect to the device.
So it means that to change the effect from HA, we would have to copy those effects and push them from HA each time. 
If it's possible for the "default effects" this would however override the mapping made from the app.
And for the "custom effect" (or defaults with mapping) it would require a way to extract the effect from the twinkly app,
which does not seam to be supported.

## Road map
- [x] Configure HACS
- [ ] Add this repo to the default repo of HACS: _[in progress](https://github.com/hacs/default/pull/107)_
- [x] Add support of online / offline (and make sure that we don't have to restart HA when we plug-in a device)
- [ ] Add discovery of devices on LAN
- [ ] Add support of floating IP adress
- [ ] Merge as a component in the HA repo

## Thanks and ref
https://labs.f-secure.com/blog/twinkly-twinkly-little-star

https://github.com/joshkay/home-assistant-twinkly

https://xled-docs.readthedocs.io/en/latest/rest_api.html
