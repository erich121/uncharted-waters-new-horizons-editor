"""Battle-menu-only mate automation toggle; retains native turn and duel paths."""
from expansion import Code
from expansion import far_jump

MODE = 0x08F2
LATCH = 0x08F4
MENU = 0x08F6


def install_battle_auto(data):
    changes = []

    def write(site, payload, reason, expected=None):
        before = bytes(data[site:site+len(payload)])
        if before != (expected if expected is not None else b'\xff'*len(payload)):
            raise ValueError(f'Unexpected toggle patch bytes at {site:06X}')
        data[site:site+len(payload)] = payload
        changes.append(dict(offset=f'0x{site:06X}', size=len(payload), reason=reason,
                            before=before.hex(), after=payload.hex()))

    # 08F2..08FB lies after immutable added hull records (ending 08F1),
    # above the already-lowered native stack (077C), and below OAM (0900).
    init = Code().emit('08 c2 20 48 a9 00 00 8f f2 08 7e 8f f4 08 7e 8f f6 08 7e '
                       '8f f8 08 7e 8f fa 08 7e 68 28')
    init.emit('5c ee 59 c1')
    write(0x218800, init.finish(), 'Initialize transient mate mode at battle entry')
    write(0xD6C48, far_jump(0x22, 0x218800), 'Reset toggle at shared battle UI entry', bytes.fromhex('22 ee 59 c1'))

    route = Code().emit('af f2 08 7e 29 01 00').branch(0xD0, 'auto')
    route.emit('64 00 6b').mark('auto')
    # Original native flagship comparison, with no branch relocation required.
    route.emit('af 61 f4 7e 85 0c af 63 f4 7e 85 0e a7 0c 85 04 '
               'a0 02 00 b7 0c 29 ff 00 85 06 af 64 f4 7e 85 00 '
               'af 66 f4 7e 29 ff 00 85 02 22 e3 fd c1 6b')
    write(0x218840, route.finish(), 'Manual fleet or native flagship-only routing')
    write(0x1DBE3, far_jump(0x22, 0x218840)+bytes.fromhex('80 27'),
          'Choose mate control mode after native ownership check', bytes.fromhex('80 2b ea ea 85 0c'))

    # Clone the three argument words so the nested native routine sees its
    # original stack layout. Only this battle command-menu call sets MENU.
    menu = Code().emit('a9 01 00 8f f6 08 7e a3 08 48 a3 08 48 a3 08 48 '
                       '22 60 68 c2 68 68 68 a9 00 00 8f f6 08 7e 6b')
    write(0x2188A0, menu.finish(), 'Guard shortcut to the top-level battle command menu')
    write(0x26D95, far_jump(0x22, 0x2188A0), 'Wrap battle command menu only', bytes.fromhex('22 60 68 c2'))

    # This shared menu loop polls once per iteration. Preserve the original
    # argument and native returned DP00 before examining the held button word.
    poll = Code().emit('a3 04 48 22 c9 19 c2 68 a5 00 48 '
                       'af 56 0b 7e 29 00 20 c9 00 20').branch(0xF0, 'held')
    poll.emit('a9 00 00 8f f4 08 7e').branch(0x80, 'done')
    poll.mark('held').emit('af f6 08 7e c9 01 00').branch(0xD0, 'done')
    poll.emit('af f4 08 7e').branch(0xD0, 'consume')
    poll.emit('a9 01 00 8f f4 08 7e af f2 08 7e 49 01 00 29 01 00 8f f2 08 7e '
              '22 40 89 e1')
    poll.mark('consume').emit('a9 00 00 83 01')
    poll.mark('done').emit('68 85 00 6b')
    write(0x2188D0, poll.finish(), 'Debounced Select toggle at live menu input polling')
    write(0x7159F, far_jump(0x22, 0x2188D0), 'Inspect shortcut while menu waits for input', bytes.fromhex('22 c9 19 c2'))

    # Native message overlay save/open/text/wait/close/restore. Preserve menu
    # cursor and event state, and clear guard while the acknowledgement is open.
    notice = Code().emit('08 c2 30 48 da 5a')
    for dp in range(0, 0x2C, 2):
        notice.emit(bytes([0xD4, dp]))
    saved = (0xE8F6, 0xE8F8, 0xA233, 0xA235, 0xA237, 0xA239, MENU)
    for address in saved:
        notice.emit(bytes([0xAF, address & 255, address >> 8, 0x7E, 0x48]))
    notice.emit('a9 00 00 8f f6 08 7e 22 c7 21 c2 f4 00 00 22 0e 79 c1 68 '
                'f4 e1 00 af f2 08 7e').branch(0xF0, 'manual')
    notice.emit('f4 00 8b').branch(0x80, 'text')
    notice.mark('manual').emit('f4 40 8b')
    notice.mark('text').emit('22 43 3c c2 68 68 22 96 70 c2 '
                            'f4 00 00 22 6a 77 c1 68 22 d8 21 c2')
    for address in reversed(saved):
        notice.emit(bytes([0x68, 0x8F, address & 255, address >> 8, 0x7E]))
    for dp in reversed(range(0, 0x2C, 2)):
        notice.emit(bytes([0x68, 0x85, dp]))
    notice.emit('7a fa 68 28 6b')
    write(0x218940, notice.finish(), 'Native acknowledgement with menu state preserved')
    write(0x218B00, b'Mates: AUTO ON.\0', 'Automatic mate mode message')
    write(0x218B40, b'Mates: AUTO OFF.\0', 'Manual mate mode message')
    return dict(enabled=True, shortcut='Select at main battle command menu',
                acknowledgement='Press A to dismiss mode confirmation',
                default='Manual mates at every new battle',
                applies='Next ship turn; flagship always manual; enemies native AI',
                storage='Transient WRAM 08F2..08FB including last manual actor; normal SRAM layout unchanged',
                changes=changes)

