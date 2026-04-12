import os
import sys

# Append the current directory so modules load correctly
sys.path.append(os.path.dirname(__file__))

from kipy.kicad import KiCad
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LiveVerify")

def run():
    socket_path = "C:/Users/Bibek/AppData/Local/Temp/kicad/api.sock"
    log.info(f"Connecting to KiCad via {socket_path}")
    try:
        kicad = KiCad(socket_path=socket_path)
        board = kicad.get_board()
        if board:
            log.info(f"Connected successfully. Board name: {getattr(board, 'name', 'unknown')}")
            
        try:
            sch = kicad.get_schematic()
            log.info("Schematic object retrieved successfully.")
            
            commit = sch.begin_commit()
            
            # Place symbols
            try:
                sym_d = sch.create_symbol(lib_id="Device:LED", reference="D99", position=(150, 150), rotation=0)
                log.info("D99 created")
            except Exception as e:
                log.warning(f"create_symbol failed: {e}")
                
            try:
                sym_r = sch.create_symbol(lib_id="Device:R", reference="R99", position=(140, 150), rotation=0)
                log.info("R99 created")
            except Exception as e:
                log.warning(f"create_symbol failed: {e}")

            # Power symbols
            try:
                sch.create_symbol(lib_id="power:+3V3", reference="#PWR_3V3", position=(140, 140), rotation=0)
                sch.create_symbol(lib_id="power:GND", reference="#PWR_GND", position=(150, 160), rotation=0)
            except Exception as e:
                log.warning(f"power symbols failed: {e}")

            try:
                sch.annotate()
                log.info("Annotated")
            except Exception as e:
                log.warning(f"annotate failed: {e}")

            sch.push_commit(commit, "Phase 8.1 Live Verification")
            log.info("Live Transaction Complete")

        except AttributeError as ae:
            log.error(f"KiCad object does not have schematic support: {ae}")
        except Exception as se:
            log.error(f"Schematic API error: {se}")

    except Exception as e:
        log.error(f"Failed to connect: {e}")

if __name__ == "__main__":
    run()
