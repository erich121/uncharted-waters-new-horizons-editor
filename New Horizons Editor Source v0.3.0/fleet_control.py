"""Optional manual fleet control, Select automation and turn camera focus."""
import struct
from battle_auto import install_battle_auto
from expansion import Code


def apply_manual_fleet(original):
    site=0x1DBE3
    before=bytes.fromhex('af 61 f4 7e')
    after=bytes.fromhex('80 2b ea ea')
    if original[site:site+4]!=before:
        raise ValueError('Unsupported battle dispatcher; expected native flagship comparison')
    data=bytearray(original)
    if len(data)==0x200000:
        data.extend(b'\xff'*0x200000);data[0xffd7]=0x0c
    if len(data)!=0x400000:raise ValueError('Unsupported Fleet Control ROM size.')
    stack=bytes(data[0x8021:0x8025])
    if stack not in (bytes.fromhex('a2 fc 08 9a'),bytes.fromhex('a2 7c 07 9a')):raise ValueError('Unexpected native stack setup.')
    data[0x8021:0x8025]=bytes.fromhex('a2 7c 07 9a')
    original=bytes(data)
    data[site:site+4]=after
    # Mates always focus. Returning to the flagship after a different manual
    # actor also focuses, even if it remains inside the native viewport.
    focus_site=0x1DC14
    if original[focus_site:focus_site+4]!=bytes.fromhex('22 43 d9 c1'):
        raise ValueError('Unsupported manual-command entry')
    focus_helper=0x218700
    flagship_visibility=bytes.fromhex(
        'af 64 f4 7e 85 0c af 66 f4 7e 29 ff 00 85 0e '
        'a0 04 00 b7 0c 85 00 4a 4a 4a 4a 4a 48 '
        'a5 00 29 1f 00 48 22 57 1c cd 68 68 a5 00 d0 04 '
        '22 6b a6 c1 5c 43 d9 c1')
    camera=Code().emit(
        'af 61 f4 7e 85 0c af 63 f4 7e 85 0e a7 0c 85 04 '
        'a0 02 00 b7 0c 29 ff 00 85 06 af 64 f4 7e 85 00 '
        'af 66 f4 7e 29 ff 00 85 02 22 e3 fd c1 a5 00')
    camera.branch(0xD0,'focus')
    camera.emit('af f8 08 7e').branch(0xF0,'visibility')
    camera.emit('cf 64 f4 7e').branch(0xD0,'focus')
    camera.emit('af 66 f4 7e 29 ff 00 cf fa 08 7e').branch(0xD0,'focus')
    camera.mark('visibility').emit(flagship_visibility[:-8])
    camera.mark('focus').emit(flagship_visibility[-8:-4])
    camera.emit('af 64 f4 7e 8f f8 08 7e af 66 f4 7e 29 ff 00 8f fa 08 7e')
    camera.emit(flagship_visibility[-4:])
    helper=camera.finish()
    if original[focus_helper:focus_helper+len(helper)]!=b'\xff'*len(helper):
        raise ValueError('Camera helper overlaps existing ROM data')
    data[focus_helper:focus_helper+len(helper)]=helper
    data[focus_site:focus_site+4]=bytes.fromhex('22 00 87 e1')
    auto=install_battle_auto(data)
    data[0xFFDC:0xFFE0]=bytes.fromhex('ff ff 00 00')
    checksum=sum(data)&65535
    struct.pack_into('<HH',data,0xFFDC,checksum^65535,checksum)
    return bytes(data),dict(enabled=True,experimental=True,patch_site='C1:DBE3',
                           before=before.hex(),after=after.hex(),
                           mode='Flagship manual; mates switch between manual and native AI',
                           camera_focus='Focus manual mates and return to flagship after a different manual actor; initial/same flagship retains visibility rule',
                           camera_hook='C1:DC14',camera_helper='E1:8700',camera_helper_bytes=helper.hex(),
                           toggle_implemented=True,auto_toggle=auto,live_battle_validation_complete=False)
