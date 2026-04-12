from collections import defaultdict
from skidl import Pin, Part, Alias, SchLib, SKIDL, TEMPLATE

from skidl.pin import pin_types

SKIDL_lib_version = '0.0.1'

__main__ = SchLib(tool=SKIDL).add_parts(*[
        Part(**{ 'name':'Micro_SD_Card', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'Micro_SD_Card'}), 'ref_prefix':'J', 'fplist':[''], 'footprint':'Connector_Card:microSD_HC_Molex_104031-0811', 'keywords':'connector SD microsd', 'description':'Micro SD Card Socket', 'datasheet':'https://www.we-online.com/components/products/datasheet/693072010801.pdf', 'pins':[
            Pin(num='1',name='DAT2',func=pin_types.BIDIR,unit=1),
            Pin(num='2',name='DAT3/CD',func=pin_types.BIDIR,unit=1),
            Pin(num='3',name='CMD',func=pin_types.INPUT,unit=1),
            Pin(num='4',name='VDD',func=pin_types.PWRIN,unit=1),
            Pin(num='5',name='CLK',func=pin_types.INPUT,unit=1),
            Pin(num='6',name='VSS',func=pin_types.PWRIN,unit=1),
            Pin(num='7',name='DAT0',func=pin_types.BIDIR,unit=1),
            Pin(num='8',name='DAT1',func=pin_types.BIDIR,unit=1),
            Pin(num='SH',name='SHIELD',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'C', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'C'}), 'ref_prefix':'C', 'fplist':[''], 'footprint':'Capacitor_SMD:C_0402_1005Metric', 'keywords':'cap capacitor', 'description':'Unpolarized capacitor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] })])