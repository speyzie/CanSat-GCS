# CanSat 2027 Ground Station

Ground control station for the CanSat 2027 PocketQube mission (Mission Guide rev 1.2).
Python 3.13, PyQt6, pyqtgraph.

## Run

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

Select the ground radio under **Radio**, enter the team number and press
**Connect**. Team, port and baud rate are remembered for the next start.

## Screen layout

Designed for a single laptop screen (1440×900 and up), so the whole ground
station fits on one 6 ft table (GS18):

```
┌ header: team · radio · connect · link · UTC clock ──────────────────────┐
│ CONTAINER  state · altitude · received · missed · packet # · mode · echo │
│ POCKETQUBE state · altitude · received · missed · packet # · mode · echo │
├ Container | PocketQube | Simulation | Console      [CSV] [Export] [New] ┤
│ telemetry card │ plot cards (latest value large)       │ command column │
└────────────────┴───────────────────────────────────────┴────────────────┘
```

* **Status strip** – both devices on every page (GS1). "Last packet" turns
  amber after 2 s and red after 5 s; "Missed" counts gaps in PACKET_COUNT.
* **Container / PocketQube pages** – required plots (GS2, GS4) with the
  latest value next to each title; every other field in the telemetry card
  (GS3, GS5). The PocketQube page opens automatically when the PocketQube
  starts transmitting.
* **Command column** – every mechanism command (GS6, GS17) and a
  **Command Status** list: ✔ when the device echoes the command and its
  COMMAND_COUNT increases, ✖ when no echo arrives within 3 s.
  **Release PocketQube** asks for confirmation.
* **Simulation page** – load the judges' profile, SIM ENABLE, SIM ACTIVATE,
  then SIMP at 1 Hz (GS7, GS8, GS16).
* **Console page** – CSV file names, rejected packets, custom commands and
  the event log.

## Architecture

```
main.py                    entry point
gcs/
  config.py                defaults (team ID, baud rates, data folder)
  settings.py              remembered operator preferences
  telemetry.py             packet models + CSV-line parsing
  commands.py              uplink command definitions
  command_tracker.py       command acknowledgement via CMD_ECHO
  attitude.py              roll/pitch/yaw from accelerometer + magnetometer
  csv_logger.py            Flight_<TEAM>C.csv / Flight_<TEAM>P.csv files
  simulation.py            pressure profile loading + 1 Hz playback
  links.py                 USB serial link to the ground radio
  ground_station.py        core: link → parse → filter → log → signals
  ui/                      PyQt widgets (no business logic)
    theme.py               GS12 sunlight theme (all styling lives here)
    icons/                 drop-down and spin box arrows
    widgets.py             Card, PlotCard, GpsTrackCard, PropertyList, VectorTable…
    bars.py                header bar and CSV actions
    status_strip.py        always-visible device summaries
    pages.py               Container and PocketQube pages
    simulation_page.py     simulation mode workflow
    console_page.py        files, custom commands, event log
    command_panel.py       command column with acknowledgement status
    main_window.py         composition and signal wiring
```

Data flows one way: `SerialLink` emits lines → `GroundStation` parses,
filters by team ID, logs to CSV, counts packets, matches command echoes and
emits typed packets → views draw them. Panels emit `Command` objects →
`GroundStation.send`.

## Radio bridge protocol (USB serial)

The ground ESP32 (ESP-NOW, X1–X6) or the optional XBee backup radio is
connected over USB serial and acts as a transparent bridge.

* **Downlink:** one ASCII telemetry packet per line, exactly in the Mission
  Guide CSV format, terminated by CR (LF also accepted).
* **Uplink:** `CMD,<TEAM_ID><C|P>,<NAME>[,<ARG>...]` + CRLF. The bridge sends
  the command only to the addressed device's MAC (X5), never broadcast (X6).
* **Echo:** the flight software reports the command in CMD_ECHO without
  commas, e.g. `MECBOOMDEPLOY`; the GCS uses this for acknowledgement.

| Button | Uplink | Echo |
|---|---|---|
| Set UTC Time | `CMD,1000C,ST,13:35:59` | `ST13:35:59` |
| Calibrate | `CMD,1000C,CAL` | `CAL` |
| Arm | `CMD,1000C,ARM` | `ARM` |
| Release PocketQube / Close Release | `CMD,1000C,MEC,RELEASE,OPEN` / `CLOSE` | `MECRELEASEOPEN` |
| Camera On / Off | `CMD,1000P,CAM,ON` / `OFF` | `CAMON` |
| Solar Panel 1 / 2 | `CMD,1000P,MEC,PANEL1,DEPLOY` | `MECPANEL1DEPLOY` |
| Deploy Boom | `CMD,1000P,MEC,BOOM,DEPLOY` | `MECBOOMDEPLOY` |
| Rotate CW / CCW | `CMD,1000P,CAM,ROT,+90` / `-90` | `CAMROT+90` |
| Simulation | `CMD,1000C,SIM,ENABLE` / `ACTIVATE` / `DISABLE` | `SIMENABLE` |
| Simulated pressure | `CMD,1000C,SIMP,101325` | `SIMP101325` |

Simulation commands go to both devices. The PocketQube is unpowered while
stowed, so it only accepts commands after release; send **SIM ENABLE** and
**SIM ACTIVATE** again after the release to switch it into simulation mode too.

The pressure profile may contain plain values (`101325`) or command lines
(`CMD,$,SIMP,101325`); the last field of each line is used and `#` lines are
ignored.

PocketQube trailing fields: the first one after `CMD_ECHO` is shown as image
stabilization data, any further fields as science experiment data.

## Requirement coverage

| Req. | Implementation |
|---|---|
| GS1 | Both devices always visible in the status strip, detailed pages per device |
| GS2 | Container altitude, temperature, battery current plots |
| GS3, GS5 | Telemetry cards and mechanism badges for all non-plotted fields |
| GS4 | PQ altitude, temperature, voltage, current, orientation (roll/pitch/yaw from sensors), GPS track, solar voltages |
| GS6, GS17 | Command column for every mechanism, custom commands on the Console page |
| GS7, GS8, GS16 | Simulation page: load profile, SIM ENABLE + ACTIVATE, SIMP at 1 Hz |
| GS11 | Received packet counters per device in the status strip (reset with **New Flight**) |
| GS12 | Light theme, near-black text, ≥14 pt fonts (live values 22 pt), 3 px traces, 2 px bold axes |
| GS13 | `flight_data/Flight_<TEAM>C.csv` and `Flight_<TEAM>P.csv` with headers, written live; **Export CSV to USB** |
| X4 | Packets from other team IDs are counted and discarded |
| F3 | **Set UTC Time** |

GS9, GS10 and GS15 (battery, antenna, portability) are hardware
requirements; the software supports GS18 by fitting on one laptop screen.
