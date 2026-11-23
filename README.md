# Flyer FIT E-Bike for Home Assistant

Read-only Home Assistant custom integration for Flyer e-bikes with the **FIT 2.0** system
over Bluetooth — directly or through ESPHome Bluetooth proxies. Completely local, no cloud,
and no QR card or account required.

## What you get (per bike)

| Entity | Notes |
|---|---|
| Battery | State of charge in % |
| Range | Remaining range in km, as shown on the display |
| Odometer | Total distance in km |
| Assist mode | Off / Eco / Standard / Auto / High |
| Powered on | On while the bike's system is switched on |
| Riding time | Total hours the wheel has turned |
| Charging | On while the charger is connected |
| Battery power | Watts; negative while charging, about 11 W when idle |
| Battery voltage, Battery current | Diagnostic; current is negative while charging |

The bike only broadcasts while it is switched on. The integration reads it shortly after it
is switched on and every 2 minutes while it stays on. While the bike is off, the sensors
keep their last values (also across Home Assistant restarts), so the battery level of a
parked bike stays visible.

**Read-only:** the integration only reads standard Bluetooth GATT characteristics and
subscribes to notifications on characteristic `0001` (required for the display to publish
unscrambled readings). It never modifies any setting on the bike.

## Requirements

- Home Assistant with Bluetooth: a local adapter, or an ESPHome Bluetooth proxy
  **with active connections** (`bluetooth_proxy: active: true`) near where the bike parks.
- The bike can hold only one Bluetooth connection at a time. While Home Assistant reads
  it (a few seconds), the FIT app cannot connect, and vice versa.

## Installation

### HACS (recommended)

1. Open **HACS** in Home Assistant.
2. Open the menu (⋮) → **Custom repositories**.
3. Add `https://github.com/Bluicie/ha-flyer-fit` with category **Integration**.
4. Search for **Flyer FIT E-Bike**, download it, and restart Home Assistant.

### Manual

Copy `custom_components/flyer_fit` into your Home Assistant `config/custom_components/`
directory and restart Home Assistant.

### Adding your bike

Switch the bike on near a Bluetooth adapter or proxy. It appears automatically under
**Settings → Devices & services → Discovered**. You can also add it manually via
**Add integration → Flyer FIT E-Bike**.

If the bike requests Bluetooth pairing, the integration pairs automatically on its first
read.

## ESP32 as a Bluetooth proxy near the bike

Any ESP32 (including ESP32-WROOM and ESP32-C3) works:

1. Open <https://esphome.github.io/bluetooth-proxies/> in Chrome or Edge.
2. Connect the ESP32 over USB, select your board, click **Connect**, and install.
3. Enter your Wi-Fi credentials when prompted. Home Assistant discovers it automatically.
4. Place it within a few metres of where the bike is parked.

## Protocol notes

The display (Sigma Elektro) exposes Bluetooth GATT service `0xFD6D` with characteristics
`0000000X-abab-4499-b9d7-d0efc0d06477`:

| Char | Bytes | Meaning |
|---|---|---|
| `0003` | 0 | Battery state of charge (%) |
| `0003` | 1–2 | Battery current in mA (`int16` LE, negative while charging) |
| `0003` | 3–4 | Battery voltage in mV (`uint16` LE) |
| `0003` | 6 | Remaining range in km for the current assist mode (frozen while charging) |
| `0004` | 2 | `0x02` while the charger is connected |
| `0001` | 0–1 | Live speed in 0.1 km/h |
| `0005` | 0–3 | Odometer in metres (`uint32` LE) |
| `0005` | 4–7 | Riding time in seconds (`uint32` LE) |
| `0006` | tail | Length byte + assist mode names separated by `0x1E` |
| `0007` | 0 | Index of the current assist mode |

**Download diagnostics** on the device page includes the raw characteristic bytes (serial
and Bluetooth address redacted) to help identify additional fields.

## Development

```bash
pip install -r requirements_test.txt
ruff check custom_components tests
pytest tests
```

## License

MIT — see [LICENSE](LICENSE).
