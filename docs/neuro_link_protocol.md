# NeuroLink Live-Socket Protocol

NeuroLink enables bidirectional, real-time sync between the standalone AI compiler and the KiCad 10 RAM session using local TCP sockets.

## Transport
- **Protocol**: TCP Socket
- **Address**: `127.0.0.1` (localhost)
- **Port**: `4242`
- **Encoding**: UTF-8 encoded JSON objects, delineated by newline (`\n`).

---

## JSON Specification

### 1. `query_state`
Queries the active KiCad 10 canvas for all footprint positions.
- **Request**:
  ```json
  { "action": "query_state" }
  ```
- **Response**:
  ```json
  {
    "status": "ok",
    "action": "query_state",
    "footprints": [
       { "ref": "U1", "x": 10.5, "y": 20.0 },
       { "ref": "J1", "x": 30.1, "y": 14.2 }
    ]
  }
  ```

### 2. `place_footprint`
Commands KiCad 10 to move a specific component reference to an exact (X, Y) coordinate in `mm`.
- **Request**:
  ```json
  {
    "action": "place_footprint",
    "ref": "J1",
    "x": 32.5,
    "y": 28.25
  }
  ```
- **Response**:
  ```json
  { "status": "ok", "action": "place_footprint" }
  ```

### 3. `route_trace`
Draws a single PCB track segment immediately and binds it to the layer.
- **Request**:
  ```json
  {
    "action": "route_trace",
    "x1": 10.0,
    "y1": 10.0,
    "x2": 15.0,
    "y2": 15.0,
    "width_mm": 0.15,
    "layer": "F.Cu"
  }
  ```
- **Response**:
  ```json
  { "status": "ok", "action": "route_trace" }
  ```

### 4. `refresh`
Forces an explicit UI & Canvas refresh within the KiCad 10 editor so users see changes instantaneously.
- **Request**:
  ```json
  { "action": "refresh" }
  ```
- **Response**:
  ```json
  { "status": "ok", "action": "refresh" }
  ```

---

## Calibration Test: Conflict Guard
To verify the live sync works without file saves:
1. Start the NeuroLink plugin in KiCad 10.
2. Ensure the standard NeuroBoard orchestration pipeline is running.
3. Manually select the **40-pin GPIO** footprint in the KiCad 10 layout and move it slightly.
4. Run the AI pipeline (`python main.py "Validate existing Raspberry Pi HAT design"`).
5. Watch the terminal for Delta Analysis. The AI will cross-reference its internal Python cache against the socket RAM response and log:
   `[LiveState] User Manual Edit detected on J1 ...`
6. Any upcoming AI auto-routes that intersect this newly manual-moved footprint will trigger the **Conflict Guard** output instantly.
