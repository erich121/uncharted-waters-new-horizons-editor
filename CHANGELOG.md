# Changelog

## v0.1.0 Beta — October 13, 2026

Initial public beta release of the Windows ship editor for the original USA SNES version of *Uncharted Waters: New Horizons*.

### Features

- Edit all 25 original ship classes, including names, hull strength, turning, sailing power, gun limits, crew limits, and base purchase prices.
- Display ship prices in gold bars.
- Save and load JSON projects, with a backup of the previous project when saving over it.
- Export a separate, headerless modified ROM, an IPS patch for the original USA ROM, and a detailed change report.
- Preserve existing export files rather than silently overwriting them.
- Distribute a standalone Windows executable with Python and Tk included.

### Compatibility and Validation

- Check that the input matches the supported original USA ROM revision.
- Accept ROMs with or without a 512-byte copier header, as well as ZIP archives containing a single ROM.
- Validate edit limits, project data, ROM checksums, and IPS patch reconstruction.

### Known Limitations

- Only the supported original USA ROM revision is accepted; previously patched ROMs are not supported as input.
- Editing is limited to existing ships. This release does not add new ship classes or edit portraits, shipyard inventories, fleets, scenarios, or game-engine behavior.
- Ship compartments, artwork, and other unsupported game data remain unchanged.
- Gameplay balance and full-campaign compatibility of user changes have not been fully verified. Test exported modifications in an emulator.

**No game ROM is included.** Users must provide their own compatible ROM.