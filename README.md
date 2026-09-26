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

## Entities

| Entity | Description |
|---|---|
| `sensor.<city>_imsak` … `_isha` | Today's Imsak, Sunrise, Dhuhr, Asr, Maghrib, Isha (timestamps) |
| `sensor.<city>_next_prayer` | Time of the next prayer; attribute `prayer` = `imsak`/`dhuhr`/`asr`/`maghrib`/`isha` |
| `sensor.<city>_hijri_date` | Hijri date; moon phase as picture, `qibla_time` attribute |

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
