# Research Dossier: Hardware & Budget

| Field | Value |
|-------|-------|
| Slug | `whole-house-audio-llm-control` |
| Phase | `concept` (hardware supplement) |
| Timestamp | `20260407T015500Z` |
| Depth | `standard` |
| Budget | `$200 max` |

## Summary

The complete hardware bill of materials comes in at **$50–$130** depending on what Pi accessories you already have, well within the $200 budget. The two critical purchases are a USB audio interface ($19–25) and an RCA Y-splitter ($5–8). Everything else depends on the state of your existing Pi setup.

## Bill of Materials

### Tier 1: Must Buy (you don't have these)

| Item | Purpose | Price | Where |
|------|---------|-------|-------|
| **Behringer UCA202** | USB audio interface — RCA stereo in, USB to Pi, plug-and-play on Linux | $19–25 | Amazon, Sweetwater, Guitar Center |
| **RCA Y-splitter (pair)** | Split phono amp output: one leg to existing amp/speakers, one leg to UCA202 | $5–8 | Amazon ("RCA Y-adapter female to 2 male") |
| **RCA cable (pair, short)** | UCA202 input to Y-splitter output (~1-2ft) | $5–8 | Amazon (may come with UCA202) |

**Tier 1 total: ~$30–40**

### Tier 2: Pi Setup (depends on what you have)

| Item | Already have? | Purpose | Price if needed |
|------|--------------|---------|-----------------|
| **Raspberry Pi** (3B+, 4, or 5) | YES (per user) | Home agent — Cast control, audio capture, streaming | $0 |
| **microSD card** (32GB+, Class 10 / A1) | Check | Boot drive for Pi OS | $8–12 |
| **USB-C power supply** (5V/3A for Pi 4, 5V/2.5A for 3B+) | Check | Power the Pi | $10–15 |
| **Case with heatsink/fan** | Check | Keep Pi cool running 24/7 | $10–15 |
| **Ethernet cable** | Check | More reliable than WiFi for always-on service (optional but recommended) | $5–8 |

**Tier 2 total: $0–50** (depending on what you already have)

### Tier 3: Optional Upgrades

| Item | Purpose | Price | When |
|------|---------|-------|------|
| **HiFiBerry DAC2 ADC Pro** | Higher-quality ADC for vinyl (192kHz/24-bit, low noise) — replaces UCA202 | $65 | If vinyl quality matters enough to upgrade |
| **USB SSD (120GB+)** | Store music collection on Pi with better reliability than SD card | $20–30 | If hosting a large local music library |
| **USB hub (powered)** | If Pi runs out of USB ports (UCA202 + SSD + other) | $10–15 | If needed |

### Budget Summary

| Scenario | Total |
|----------|-------|
| **Minimum** (have all Pi accessories) | ~$30 |
| **Typical** (need SD card + power supply + case) | ~$65–80 |
| **Full setup** (need everything except Pi board) | ~$100–130 |
| **Audiophile vinyl** (HiFiBerry DAC2 ADC Pro upgrade) | add ~$40 over UCA202 |

**All scenarios fit within $200 with room to spare.**

## Hardware Deep Dives

### Behringer UCA202 — Why This One

- **$19-25** — cheapest viable option that actually works
- **RCA in/out** — matches your phono amp's RCA output directly, no adapter needed
- **USB class-compliant** — no drivers on Linux/Pi, shows up as ALSA device immediately
- **48 kHz / 16-bit** — adequate for vinyl streaming to Cast (Cast itself maxes at 48kHz for most formats)
- **USB-powered** — no separate power supply needed
- **4,000+ Amazon reviews, 4.5 stars** — proven at this price point
- The UCA222 is identical internals, different color ($19 at Thomann)

**Alternative considered**: Behringer UFO202 ($15) — same thing but has a **built-in phono preamp**. Since you already have an external phono amp, you don't need this, and the UFO202's preamp can't be bypassed cleanly. Stick with UCA202.

**Higher-end alternative**: HiFiBerry DAC2 ADC Pro ($65) — Pi HAT (plugs directly on GPIO), 192kHz/24-bit, very low noise floor. Can even accept a turntable signal directly without a phono preamp (has adjustable gain, -10dB to +40dB). Worth considering if vinyl quality is a priority, but the UCA202 is fine for streaming to Cast speakers.

### RCA Y-Splitter — No Quality Loss

Consensus from AudioScienceReview, AudioKarma, and Steve Hoffman Forums: **Y-splitters cause zero audible degradation** when splitting a line-level signal (like phono preamp output) to two destinations, as long as both destinations have normal input impedance (>10kΩ, which the UCA202 and your amp both have).

**Where to split**: After the phono amp, before the A/B selector.

```
Turntable → Phono Amp → [Y-Splitter] → Leg A: A/B Selector → Speakers (unchanged)
                                       → Leg B: UCA202 → Pi (new)
```

Your existing speaker setup is completely untouched. The Y-splitter just taps a copy of the signal.

### Raspberry Pi — Pi 4 is the Sweet Spot

- **Pi 4 (4GB)**: Runs Docker, Music Assistant, Icecast, Tailscale, and pychromecast simultaneously without breaking a sweat. USB 3.0 for fast SSD if needed. Gigabit ethernet.
- **Pi 3B+**: Can do it but will be tight running Docker + MA. Only USB 2.0, 100Mbit ethernet. Acceptable for a lighter setup (just pychromecast + icecast, no MA).
- **Pi 5**: Overkill but if you have one, use it.

**Headless setup** (no monitor/keyboard needed): Flash Raspberry Pi OS Lite to SD card with SSH enabled, connect ethernet, configure everything via SSH from this VPS or your laptop.

### Wiring Diagram

```
┌──────────┐     ┌──────────┐     ┌─────────────┐
│ Turntable│────▶│ Phono Amp│────▶│ Y-Splitter  │
└──────────┘     └──────────┘     └──────┬──────┘
                                         │
                          ┌──────────────┤
                          │              │
                          ▼              ▼
                   ┌────────────┐  ┌──────────┐
                   │ A/B Switch │  │ UCA202   │
                   │ (existing) │  │ (USB)    │
                   └─────┬──────┘  └────┬─────┘
                         │              │ USB
                    ┌────┴────┐    ┌────▼─────┐
                    │ Zone A  │    │ Rasp Pi  │
                    │ Zone B  │    │ (home    │
                    │speakers │    │  agent)  │
                    └─────────┘    └────┬─────┘
                                       │ Google Cast
                              ┌────────┼────────┐
                              ▼        ▼        ▼
                          Kitchen   Bedroom   Office
                          (Nest)   (Nest)    (Home)
```

## What To Buy — Shopping List

**Order today (essential):**
1. Behringer UCA202 — Amazon/Sweetwater ~$25
2. RCA Y-splitter adapters (1 pair, female-to-2-male) — Amazon ~$6
3. Short RCA cable pair (if not included with UCA202) — Amazon ~$6

**Check if you have, buy if not:**
4. microSD card 32GB+ (Samsung EVO Select or SanDisk Extreme) — ~$10
5. USB-C power supply 5V/3A (official Pi foundation one is best) — ~$12
6. Pi case with passive heatsink or fan — ~$10
7. Ethernet cable (Cat5e/Cat6, whatever length you need from router to Pi) — ~$5-8

**Don't buy yet (evaluate first):**
- HiFiBerry DAC2 ADC Pro — only if vinyl quality through Cast isn't good enough with UCA202
- USB SSD — only if you're storing a large local music collection on the Pi

## Sources

1. [Behringer UCA202 — Equipboard pricing](https://equipboard.com/items/behringer-uca202-usb-audio-interface) — $16-25 across 8 stores
2. [Behringer UCA202 — Official](https://www.behringer.com/product.html?modelCode=P0484) — $18.90 MSRP
3. [UCA202 on Linux](https://larrytalkstech.com/behringer-uca202-uca222-usb-audio-interface-linux/) — ALSA setup guide
4. [RCA Y-splitter quality — AudioScienceReview](https://www.audiosciencereview.com/forum/index.php?threads/rca-splitter-y-adapter-do-they-degrade-sound-quality.24074/) — No degradation with line-level signals
5. [Y-splitter for phono preamp — AudioKarma](https://audiokarma.org/forums/threads/can-i-use-a-y-splitter-to-run-phono-preamps-out-to-2-devices-an-amp-a-adc-interface.914792/) — Confirmed working for turntable + ADC split
6. [HiFiBerry turntable guide](https://www.hifiberry.com/blog/adding-a-turntable-to-your-pi-based-audio-system/) — Turntable → Pi architecture overview
7. [HiFiBerry ADC comparison](https://www.hifiberry.com/docs/hardware/comparison-of-hifiberry-cards-for-audio-recording/) — DAC+ ADC vs DAC2 ADC Pro
8. [Pi music server guide 2025](https://www.musicservertips.com/setup-guides/raspberry-pi-music-server-guide/) — Pi 4 sweet spot, headless setup
9. [Pi USB audio + ALSA](https://learn.adafruit.com/usb-audio-cards-with-a-raspberry-pi/updating-alsa-config) — Driver-free setup
10. [Pi audio recording](https://forum.core-electronics.com.au/t/use-raspberry-pi-to-record-audio/8013) — UCA202 recommended for vinyl capture
