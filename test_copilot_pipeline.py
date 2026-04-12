import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'ai_core')
from copilot.intent_parser import IntentParser
from copilot.component_intelligence import ComponentIntelligence
from copilot.library_fetcher import LibraryFetcher

parser = IntentParser()
intel  = ComponentIntelligence()

prompt   = "Create a Raspberry Pi HAT with Hailo-8 and dual SD card slots"
spec     = parser.parse(prompt)
manifest = intel.suggest_components(spec)

print("=== INTENT PARSER OUTPUT ===")
print(f"Form Factor : {spec['form_factor']['id']}")
print(f"Accelerator : {spec['accelerator']['id'] if spec.get('accelerator') else 'None'}")
print(f"Features    : {[f['id'] for f in spec['features']]}")
print(f"Interfaces  : {spec['interfaces']}")
print(f"Board Size  : {spec['constraints'].get('board_width_mm')}mm x {spec['constraints'].get('board_height_mm')}mm")
print()
print("=== COMPONENT INTELLIGENCE OUTPUT ===")
print(f"Unique entries : {len(manifest['components'])}")
print(f"Total parts    : {manifest['total_count']}")
print(f"Warnings       : {manifest['warnings']}")
print()
print("=== BILL OF MATERIALS ===")
for item in manifest['bom_preview']:
    print(f"  {item['quantity']}x  {item['component']}  [{item['value']}]")

print()

# Library fetcher stats
fetcher = LibraryFetcher()
stats = fetcher.get_cache_stats()
print("=== LIBRARY CACHE ===")
print(f"Cached entries : {stats['total_cached']}")
print(f"Lib directory  : {stats['lib_dir']}")
