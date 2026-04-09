import os, sys, re, json

lib_dir = r"C:\Users\Bibek\NeuroBoard\lib\footprint"
fp_files = [f for f in os.listdir(lib_dir) if f.endswith(".kicad_mod")]

for fp_file in fp_files:
    if "APCI0107" in fp_file or "C2935243" in fp_file or "FPC" in fp_file:
        with open(os.path.join(lib_dir, fp_file), "r", encoding="utf-8") as f:
            content = f.read()
        pads = re.findall(r'\(pad\s+"([^"]*)"', content)
        print(f"{fp_file}: pads={len(pads)}")
        print(f"Pads: {pads}")
