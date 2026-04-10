# Raspberry Pi AI HAT+ Hardware Specification

This document strictly defines the physical, mechanical, and electrical compliance rules for the Raspberry Pi AI HAT+ hosting an M.2-based Hailo-8 AI Accelerator module.

## 1. Mechanical Requirements (Board Outline & Drill)

### Dimensions
- **Width:** 65.00 mm
- **Length:** 56.50 mm
- **Corner Radii:** Required smoothly rounded contours along the primary HAT boundaries (typically 3mm radii).

### Mounting Holes (M2.5)
Four M2.5 mounting holes aligned precisely to the Raspberry Pi standard grid:
1. `Top-Left`:      [x: 3.50 mm, y: 3.50 mm]
2. `Top-Right`:     [x: 61.50 mm, y: 3.50 mm]
3. `Bottom-Left`:   [x: 3.50 mm, y: 52.50 mm]
4. `Bottom-Right`:  [x: 61.50 mm, y: 52.50 mm]
*(Note: Coordinate origins relative to the top-left HAT datum offset).*

## 2. Component Placements 

### 40-Pin GPIO Header
- Standard 2x20 2.54mm pitch female header.
- Aligned alongside the top mechanical edge to interface directly with the Raspberry Pi GPIO bank.
- Must provide clear physical separation from the M.2 slot to avoid Z-height clashes with the module heatsink.

### FPC Connector (PCIe Line)
- Situated appropriately near the active PCIe ingress location.
- Strict requirement for mechanical keep-outs around the FPC latching mechanism.

### M.2 Slot (M-Key or E-Key)
- Designed to receive the Hailo-8 AI accelerator module securely.
- Proper thermal pad spacing integrated underneath the M.2 footprint for active heat dissipation.

## 3. Electrical Requirements

### HAT EEPROM Standard
- Requires an `AT24C32` (or compatible) EEPROM chip.
- Connections:
  - WP (Write Protect) pin mapped correctly.
  - Interfaced strictly via `ID_SD` (GPIO 0) and `ID_SC` (GPIO 1).
- Pull-ups: Requires standard ~3.9k series resistors on the ID pairs for successful HAT autodetection during boot.

### Power Regulatory Network (PDN)
- The M.2 slot delivering the Hailo-8 computational payload inherently draws substantial transients.
- Dedicated 3.3V Step-down regulatory logic (if stepping down from 5V source) must be placed optimally.
- Robust ground polygon pours explicitly verified by the PySpice integration module.

### High-Speed Routing (PCIe Gen 3.0 / 2.0)
- The differential pairs connecting the FPC slot and the M.2 pins MUST inherently match 100-ohm profiles.
- Strict length matching tolerance bounds verified down to < 0.1 mm skew thresholds using the Rust constraints engine.
