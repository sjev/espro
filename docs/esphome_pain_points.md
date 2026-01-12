# ESPHome + Home Assistant — Real Pain Points from the Community

This document collects recurring problems reported by users running ESPHome with Home Assistant, especially around device replacement, naming, and lifecycle management.

These are exactly the problems a “Control Plane” between HA and ESPHome would solve.

---

## 1. Replacing a broken ESP breaks automations and dashboards

When an ESP board dies and you flash a new one, Home Assistant sees a new device.
Even if the YAML is identical, entity IDs change and everything breaks.

**Quote**

> “I ended up creating a new device, giving all the entities different names, and redoing all the automations and the lovelace interface…”

Source:
[Best procedure to replace a failed device](https://community.home-assistant.io/t/best-procedure-to-replace-a-failed-device/546325)

---

## 2. Entity IDs depend on device names

ESPHome uses the device name as part of the unique ID.
If you rename the device or replace it, HA creates new entities.

**Quote**

> “ESPHome uses the device name to generate the default unique id. If you change the device name it’s going generate new entities.”

Source:
[Home Assistant issue #97726](https://github.com/home-assistant/core/issues/97726)

---

## 3. HA updates changed naming and broke setups

In HA 2025.5 the device name started appearing in entity names, breaking existing dashboards and automations.

**Quote**

> “After updating to HA 2025.5, all of my ESPHome entities started including the device name as a prefix… This breaks things badly.”

Source:
[HA 2025.5 ESPHome device names now on frontend](https://community.home-assistant.io/t/ha-2025-5-esphome-device-names-now-on-frontend/888042)

---

## 4. Users have to name things twice

ESPHome + Home Assistant require naming both in firmware and again in HA to get usable entities.

**Quote**

> “We have to name our entities twice… or go back and completely rename everything.”

Source:
[HA 2025.5 ESPHome device names now on frontend](https://community.home-assistant.io/t/ha-2025-5-esphome-device-names-now-on-frontend/888042)

---

## 5. There is no real “replace device” workflow

The HA team acknowledges that replacing hardware without breaking everything is not properly solved.

**Quote**

> “We need a way to replace a device while keeping entity IDs, history, and automations intact.”

Source:
[Home Assistant Architecture: Add support for device replacement](https://github.com/home-assistant/architecture/discussions/1088)

---

## 6. ESPHome name prefixing is controversial

ESPHome prepends the device name to every entity, which many users dislike and want disabled.

Source:
[ESPHome feature request: remove prefixing of friendly_name](https://github.com/esphome/feature-requests/issues/2476)
[Reddit: ESPHome device name prefixing not a welcome change](https://www.reddit.com/r/homeassistant/comments/1kiick9/esphome_device_name_prefixing_not_a_welcome/)

---

## 7. Renaming devices leaves broken or stale entities

Changing a device name in HA does not correctly migrate entity IDs.

Source:
[Home Assistant issue #77150 — Entities not renamed after device rename](https://github.com/home-assistant/core/issues/77150)

---

## 8. Substitutions cause ugly, duplicated names

Using substitutions in ESPHome YAML often results in absurd entity names in HA.

Example from a real user:
`sensor.esp_dummy_esp_dummy_connected_bssid`

Source:
[Naming ESPHome entities in HA](https://community.home-assistant.io/t/naming-esphome-entities-in-ha/702637)

---

## What all of this boils down to

Across forums, GitHub, and Reddit the same problems appear again and again:

* Hardware replacement breaks everything
* Entity identity is tied to hardware names
* Updates change naming behavior
* There is no clean lifecycle management
* Users manually repair their system after failures

ESPHome and Home Assistant both assume that **devices are stable**.

But real hardware is not.

---

## Why a Control Plane makes sense

Your Control Plane idea directly targets what the community is missing:

| Today | With a Control Plane |
|------|---------------------|
| Entities bound to ESP MAC / name | Entities bound to logical role |
| Replace device → break automations | Replace device → mapping updates |
| YAML tied to hardware | YAML tied to role |
| HA sees devices | HA sees stable logical devices |
| Users manually fix things | Infrastructure handles lifecycle |

This is not a theoretical problem.
It is one of the most common ESPHome + Home Assistant frustrations.
