# yt_dj Operational Runbook

## Quick Start

```bash
# 1. Configure API keys and stream key
vim config/stream.json    # Set youtube.stream_key, obs.password
vim config/webcams.json   # Set windy_api_key

# 2. Install systemd services
sudo cp scripts/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# 3. Start everything
sudo systemctl start yt-dj

# 4. Check status
sudo systemctl status yt-dj obs-headless liquidsoap redis-server
```

## Architecture

```
Discord/YT Chat → Chatbot → Redis Pub/Sub → OBS Controller → OBS (video)
                                           → LS Controller  → Liquidsoap (audio)
                                           → Health Monitor → Webcam feeds
                                                            ↓
                                                     YouTube RTMP
```

## Services

| Service | Port | Control |
|---------|------|---------|
| OBS WebSocket | 4455 | `obsws-python` |
| Liquidsoap telnet | 3333 | `nc localhost 3333` |
| Redis | 6379 | `redis-cli` |
| Xvfb | :99 | Display server |

## Chatbot Commands

| Command | Effect |
|---------|--------|
| `play house` / `play techno` / `play ambient` | Switch music genre |
| `night cams` / `show europe` / `traffic` | Switch webcam theme |
| `2x2` / `3x3` / `fullscreen` | Change grid layout |
| `skip` / `next track` | Skip current track |
| `volume 80` / `vol 0.5` | Adjust volume |

## Troubleshooting

### Stream not starting
```bash
# Check OBS
systemctl status obs-headless
journalctl -u obs-headless -f

# Check if Xvfb is running
ps aux | grep Xvfb

# Check YouTube stream key
cat config/stream.json | jq .youtube.stream_key
```

### No audio
```bash
# Check Liquidsoap
systemctl status liquidsoap
echo "help" | nc -q 1 localhost 3333

# Check PulseAudio
pactl list short sinks
```

### Webcam feed offline
```bash
# Check health monitor logs
journalctl -u yt-dj -f | grep health_monitor

# Manual probe
ffprobe -v quiet -i "WEBCAM_URL" -show_entries format=duration
```

### 12-hour restart
YouTube ends streams after ~12 hours. The stream manager auto-detects this and restarts. If it fails:
```bash
systemctl restart yt-dj
```

### OBS memory leak
OBS headless can leak memory over days. The systemd watchdog restarts it if unresponsive. Force restart:
```bash
systemctl restart obs-headless
```

## Manual Redis Commands

```bash
# Publish a command directly
redis-cli PUBLISH stream:audio '{"action":"set_genre","params":{"genre":"house"},"source":"manual"}'
redis-cli PUBLISH stream:video '{"action":"switch_scene","params":{"scene":"night"},"source":"manual"}'
redis-cli PUBLISH stream:layout '{"action":"set_layout","params":{"layout":"3x3"},"source":"manual"}'
```

## Stop Everything

```bash
sudo systemctl stop yt-dj obs-headless liquidsoap
```
