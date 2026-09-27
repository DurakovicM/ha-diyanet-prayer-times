# Diyanet Prayer Times for Home Assistant

Official prayer times from the Turkish Presidency of Religious Affairs
(Diyanet İşleri Başkanlığı), exactly as published on
[namazvakitleri.diyanet.gov.tr](https://namazvakitleri.diyanet.gov.tr), no account needed.

Data comes from the free mirror `ezanvakti.emushaf.net`, which serves Diyanet's own
tables. The integration fetches ~32 days at a time, stores them on disk, and keeps
working from that cache if the service is temporarily unreachable.

## Installation

**HACS:** add this repository as a custom repository (type *Integration*), install
*Diyanet Prayer Times*, restart Home Assistant.

**Manual:** copy `custom_components/diyanet_prayer_times` into your
`<config>/custom_components/` folder and restart.

Then go to *Settings → Devices & services → Add integration → Diyanet Prayer Times*
and choose your country, state/province and city/district.

## Language

English, Bosanski, Deutsch, Nederlands and Türkçe. Choose the language for this
integration only under *Settings → Devices & services → Diyanet Prayer Times →
Configure* (or while adding a city). *Automatic* follows Home Assistant's system
language. It changes sensor names, the next-prayer text and the Hijri month.
Country and city names are shown as Diyanet provides them.

## Time zone

Diyanet publishes local wall-clock times. They are read in Home Assistant's time
zone by default. If you add a city in another time zone (e.g. Istanbul while your
Home Assistant is in Germany), set that city's time zone under *Configure*.

## Entities

Entity IDs start with the device name (e.g. `istanbul`) and do not depend on the
language.

| Entity | Example value | Use |
|---|---|---|
| `sensor.<city>_imsak_time` … `_isha_time` | `05:23` | Dashboards: exact published time |
| `sensor.<city>_next_prayer_time` | `Sunset 19:03` | Dashboards; attribute `prayer` = `maghrib` |
| `sensor.<city>_hijri_date` | `15 Rabi al-Thani 1448` | Moon phase picture, `qibla_time` attribute |
| `sensor.<city>_imsak` … `_isha` | timestamp | Automations (diagnostic, hidden from default dashboards) |
| `sensor.<city>_next_prayer` | timestamp | Automations; attributes `prayer`, `time` |
| `binary_sensor.<city>_ezan` | on / off | On for 1 minute at each selected prayer (motion class, for Alexa routines); attribute `prayer` |
| `switch.<city>_ezan_active` | on / off | Master switch: when off, the ezan sensor never turns on |

Prayer keys: `imsak` (Dawn), `sunrise`, `dhuhr` (Noon), `asr` (Afternoon),
`maghrib` (Sunset), `isha` (Night).

## Dashboard

The `_time` sensors show `HH:MM` on any card, no setup needed:

```yaml
type: entities
title: Prayer times
entities:
  - sensor.istanbul_next_prayer_time
  - sensor.istanbul_imsak_time
  - sensor.istanbul_sunrise_time
  - sensor.istanbul_dhuhr_time
  - sensor.istanbul_asr_time
  - sensor.istanbul_maghrib_time
  - sensor.istanbul_isha_time
  - sensor.istanbul_hijri_date
```

## Automation example

```yaml
triggers:
  - trigger: time
    at: sensor.istanbul_maghrib
actions:
  - action: notify.mobile_app_phone
    data:
      message: "Akşam vakti"
```

## Alexa: play the ezan

Choose which prayers trigger the ezan under *Configure → Call to prayer at*
(default: all five). Use `switch.<city>_ezan_active` to turn the ezan on or off,
e.g. from the dashboard or an automation when nobody is home.

The standard Alexa skill cannot receive audio from Home Assistant, but an Alexa
routine can react to `binary_sensor.<city>_ezan` (it behaves like a motion sensor):

1. *Settings → Voice assistants → Alexa*: expose `binary_sensor.<city>_ezan`.
   With Home Assistant Cloud, make sure *state reporting* is enabled.
2. "Alexa, discover devices".
3. Alexa app → *Routines → +*: **When** Smart Home → *Call to prayer* → detects
   motion; **Alexa will** e.g. Music & Podcasts → an ezan recording, or a skill;
   **From** your Echo.

## Development

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
```
