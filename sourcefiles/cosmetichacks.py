'''
Module for hacks that just change looks/sounds without changing gameplay.
'''
import ctenums

from ctrom import CTRom
# import randoconfig as cfg

import ctevent
import ctstrings
import mapmangler
import randosettings as rset


def set_pc_names(
        ct_rom: CTRom,
        crono_name: str = None,
        marle_name: str = None,
        lucca_name: str = None,
        robo_name: str = None,
        frog_name: str = None,
        ayla_name: str = None,
        magus_name: str = None,
        epoch_name: str = None
):
    '''
    Provide names to be used for characters and epoch.
    '''
    default_names = (
        'Crono', 'Marle', 'Lucca', 'Robo', 'Frog', 'Ayla', 'Magus', 'Epoch'
    )

    copy_str = bytearray()

    provided_names = (crono_name, marle_name, lucca_name, robo_name,
                      frog_name, ayla_name, magus_name, epoch_name)

    for default_name, given_name in zip(default_names, provided_names):
        if given_name == '' or given_name is None:
            given_name = default_name

        name_b = ctstrings.CTNameString.from_string(given_name, length=5,
                                                    pad_val=0)
        name_b.append(0)
        copy_str.extend(name_b)

    script = ct_rom.script_manager.get_script(ctenums.LocID.LOAD_SCREEN)
    # Finding a memcpy command (0x4E) writing to 0x7E2C32 with a payload of
    # length 0x0032
    memcpy_cmd_b = bytes.fromhex('4E232C7E3200')
    pos = script.data.find(memcpy_cmd_b)
    pos += len(memcpy_cmd_b)

    script.data[pos:pos+len(copy_str)] = copy_str[:]


def apply_quiet_mode(ct_rom: CTRom, settings: rset.Settings):
    '''
    Set the volume of all songs to 0.
    '''

    if rset.CosmeticFlags.QUIET_MODE not in settings.cosmetic_flags:
        return

    rom = ct_rom.rom_data
    rom.seek(0x07241D)

    # Volumes of music tracks stored at 0x07241D.
    # 2 Bytes per song x * 0x53 songs = 0xA6 bytes.
    payload = b'\x00' * 0xA6
    rom.write(payload)


def zenan_bridge_alt_battle_music(ctrom: CTRom, settings: rset.Settings):
    '''
    Play the unused alternate battle theme while going through Zenan Bridge
    '''
    if rset.CosmeticFlags.ZENAN_ALT_MUSIC not in settings.cosmetic_flags:
        return

    LocID = ctenums.LocID
    script_man = ctrom.script_manager

    script = script_man.get_script(LocID.ZENAN_BRIDGE)

    start = script.get_function_start(0x15, 3)
    end = script.get_function_end(0x15, 3)

    # There should only be one playsong command in that function
    pos, _ = script.find_command([0xEA], start, end)

    if pos is None:
        raise ValueError("Error finding Zenan Bridge battle song command")

    # Byte after the command id has the song id.
    script.data[pos+1] = 0x51


def death_peak_singing_mountain_music(ctrom: CTRom,
                                      settings: rset.Settings):
    '''
    Change Death Peak to use Singing Mountain music
    '''
    if rset.CosmeticFlags.DEATH_PEAK_ALT_MUSIC not in settings.cosmetic_flags:
        return

    LocID = ctenums.LocID
    death_peak_maps = [
        LocID.DEATH_PEAK_CAVE,
        LocID.DEATH_PEAK_GUARDIAN_SPAWN,
        LocID.DEATH_PEAK_LOWER_NORTH_FACE,
        LocID.DEATH_PEAK_NORTHEAST_FACE,
        LocID.DEATH_PEAK_NORTHWEST_FACE,
        LocID.DEATH_PEAK_SOUTH_FACE,
        LocID.DEATH_PEAK_SOUTHEAST_FACE,
        LocID.DEATH_PEAK_SUMMIT,
        LocID.DEATH_PEAK_UPPER_NORTH_FACE
    ]

    LocData = mapmangler.LocationData
    rom = ctrom.rom_data.getbuffer()

    for loc in death_peak_maps:
        data = LocData.from_rom(rom, loc)
        data.music = 0x52
        data.write_to_rom(rom, loc)

    script = ctrom.script_manager.get_script(LocID.DEATH_PEAK_GUARDIAN_SPAWN)

    change_music = ctevent.EC.generic_one_arg(0xEA, 0x3C)

    start = script.get_function_start(0x08, 1)
    end = script.get_function_end(0x08, 1)
    pos = script.find_exact_command(change_music, start, end)

    if pos is None:
        raise ValueError('Error finding play \'Silent light\' command')

    script.data[pos+1] = 0x52
