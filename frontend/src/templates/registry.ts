// ── Types ──────────────────────────────────────────────────────────────────

export type TemplateCategory = "RPI" | "ARDUINO" | "CUSTOM";

export interface PCBTemplate {
  id: string;
  name: string;
  description: string;
  category: TemplateCategory;
  icon: string; // emoji
  interfaces: string[];
  constraints: Record<string, any>;
  requiredModules: string[];
  compatibleModules: string[];
}

export type ModuleInterface =
  | "GPIO"
  | "PCIE"
  | "USB"
  | "I2C"
  | "SPI"
  | "UART"
  | "POWER"
  | "ANALOG";

export interface PCBModule {
  id: string;
  name: string;
  description: string;
  icon: string; // emoji
  interface: ModuleInterface;
  footprint: string;
  constraints: Record<string, any>;
  // Which templates can accept this module
  compatibleTemplates: string[];
}

export interface ActionResult {
  success: boolean;
  message: string;
  kicadUpdated?: boolean;
}

// ── Template Registry ──────────────────────────────────────────────────────

export const TEMPLATES: PCBTemplate[] = [
  {
    id: "rpi-hat",
    name: "Raspberry Pi HAT",
    description: "Standard HAT format with 40-pin GPIO. Compatible with RPi 4 and RPi 5.",
    category: "RPI",
    icon: "🍓",
    interfaces: ["GPIO", "I2C", "SPI", "UART", "PCIE"],
    constraints: {
      board_size_mm: "65x56",
      gpio_voltage: 3.3,
      max_current_ma: 500,
    },
    requiredModules: ["gpio-40pin"],
    compatibleModules: ["nvme-m2", "usb-c-port", "led-indicator", "eeprom-hat"],
  },
  {
    id: "arduino-shield",
    name: "Arduino Uno Shield",
    description: "Standard Arduino Shield footprint for stacking on top of Arduino Uno R3.",
    category: "ARDUINO",
    icon: "🔵",
    interfaces: ["GPIO", "I2C", "SPI", "UART", "ANALOG"],
    constraints: {
      board_size_mm: "68.6x53.4",
      gpio_voltage: 5.0,
      max_current_ma: 200,
    },
    requiredModules: ["arduino-headers"],
    compatibleModules: ["usb-c-port", "led-indicator", "relay-module"],
  },
  {
    id: "custom-blank",
    name: "Custom Blank PCB",
    description: "Start from scratch. No constraints. Full freedom.",
    category: "CUSTOM",
    icon: "⬜",
    interfaces: [],
    constraints: {},
    requiredModules: [],
    compatibleModules: ["gpio-40pin", "nvme-m2", "usb-c-port", "led-indicator", "arduino-headers"],
  },
];

// ── Module Registry ────────────────────────────────────────────────────────

export const MODULES: PCBModule[] = [
  {
    id: "gpio-40pin",
    name: "40-Pin GPIO Header",
    description: "Standard Raspberry Pi 40-pin GPIO header. Required for HAT form factor.",
    icon: "📌",
    interface: "GPIO",
    footprint: "Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical",
    constraints: { voltage: 3.3, pins: 40 },
    compatibleTemplates: ["rpi-hat", "custom-blank"],
  },
  {
    id: "nvme-m2",
    name: "M.2 NVMe Slot (PCIe)",
    description: "M-Key M.2 slot supporting NVMe SSDs via PCIe x1. Supports 2230 and 2242.",
    icon: "💾",
    interface: "PCIE",
    footprint: "Connector_PinHeader_1.00mm:PinHeader_1x67_P1.00mm_Vertical",
    constraints: { pcie_gen: 2, key: "M", form_factor: "2230/2242" },
    compatibleTemplates: ["rpi-hat", "custom-blank"],
  },
  {
    id: "usb-c-port",
    name: "USB-C Port",
    description: "USB 2.0 Type-C connector for power delivery and data transfer.",
    icon: "🔌",
    interface: "USB",
    footprint: "Connector_USB:USB_C_Receptacle_GCT_USB4085",
    constraints: { standard: "USB2.0", power_delivery: false },
    compatibleTemplates: ["rpi-hat", "arduino-shield", "custom-blank"],
  },
  {
    id: "led-indicator",
    name: "LED Status Indicator",
    description: "Simple status LED with current-limiting resistor for power/activity indication.",
    icon: "💡",
    interface: "GPIO",
    footprint: "LED_SMD:LED_0603_1608Metric",
    constraints: { wavelength_nm: 630, current_ma: 10 },
    compatibleTemplates: ["rpi-hat", "arduino-shield", "custom-blank"],
  },
  {
    id: "arduino-headers",
    name: "Arduino Uno Stacking Headers",
    description: "Standard Arduino Uno R3 shield headers (10+8+6+6 pins).",
    icon: "🔷",
    interface: "GPIO",
    footprint: "Connector_PinHeader_2.54mm:PinHeader_1x10_P2.54mm_Vertical",
    constraints: { voltage: 5.0 },
    compatibleTemplates: ["arduino-shield", "custom-blank"],
  },
  {
    id: "eeprom-hat",
    name: "HAT EEPROM (24AA32)",
    description: "Required EEPROM for proper Raspberry Pi HAT identification.",
    icon: "🧠",
    interface: "I2C",
    footprint: "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    constraints: { address: "0x50", size_kb: 32 },
    compatibleTemplates: ["rpi-hat", "custom-blank"],
  },
];

// ── Helpers ────────────────────────────────────────────────────────────────

export function getTemplateById(id: string): PCBTemplate | undefined {
  return TEMPLATES.find((t) => t.id === id);
}

export function getModuleById(id: string): PCBModule | undefined {
  return MODULES.find((m) => m.id === id);
}

export function getCompatibleModules(templateId: string): PCBModule[] {
  return MODULES.filter((m) => m.compatibleTemplates.includes(templateId));
}

export function isModuleCompatible(templateId: string, moduleId: string): boolean {
  const template = getTemplateById(templateId);
  if (!template) return false;
  return (
    template.compatibleModules.includes(moduleId) ||
    template.requiredModules.includes(moduleId)
  );
}
