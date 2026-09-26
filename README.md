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

## Languages

English, Turkish, Bosnian, German and Dutch. Setup screens, entity names, the
"next prayer" name and the Hijri month follow Home Assistant's system language
(*Settings → System → General*). Country and city names are shown as Diyanet
provides them.

## Entities

| Entity | Description |
|---|---|
| `sensor.<city>_imsak` … `_isha` | Today's Imsak, Sunrise, Dhuhr, Asr, Maghrib, Isha (timestamps); attribute `time` = `"05:23"` |
| `sensor.<city>_next_prayer` | Time of the next prayer; attributes `prayer` (`imsak`/`dhuhr`/`asr`/`maghrib`/`isha`) and `time` |
| `sensor.<city>_hijri_date` | Hijri date in your language; moon phase as picture, `qibla_time` attribute |

Entity IDs are created from the name in the system language at setup time, e.g.
`sensor.istanbul_maghrib` (English/German/Dutch), `sensor.istanbul_aksam`
(Turkish/Bosnian). Check *Settings → Entities* for yours.

## Dashboard

Timestamp sensors show relative time ("in 2 hours") by default. To show the
exact times, use `format: time`:

```yaml
type: entities
title: Prayer times
entities:
  - entity: sensor.istanbul_imsak
    format: time
  - entity: sensor.istanbul_sunrise
    format: time
  - entity: sensor.istanbul_dhuhr
    format: time
  - entity: sensor.istanbul_asr
    format: time
  - entity: sensor.istanbul_maghrib
    format: time
  - entity: sensor.istanbul_isha
    format: time
  - sensor.istanbul_hijri_date
```

Next prayer as a tile, e.g. "Asr · 16:22":

```yaml
type: tile
entity: sensor.istanbul_next_prayer
state_content:
  - prayer
  - time
```

Example automation:

```yaml
triggers:
  - trigger: time
    at: sensor.istanbul_maghrib
actions:
  - action: notify.mobile_app_phone
    data:
      message: "Akşam vakti"
```

## Development

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
```
