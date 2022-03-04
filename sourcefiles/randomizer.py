from __future__ import annotations

import os
import pickle
import sys

import treasurewriter
import shopwriter
import logicwriter_chronosanity as logicwriter
import random as rand
import bossrandoevent as bossrando
import bossscaler
import tabchange as tabwriter
import fastmagic
import fastpendant
import charrando
import roboribbon
import techrandomizer
import qolhacks
import cosmetichacks
import bucketfragment
import iceage
import legacyofcyrus
import mystery

import byteops
import ctenums
import ctevent
from ctrom import CTRom
import ctstrings
import enemyrewards

# from freespace import FSWriteType
import randoconfig as cfg
import randosettings as rset


class NoSettingsException(Exception):
    pass


class NoConfigException(Exception):
    pass


class Randomizer:

    def __init__(self, rom: bytearray, is_vanilla: bool = True,
                 settings: rset.Settings = None,
                 config: cfg.RandoConfig = None):

        # We want to keep a copy of the base rom around so that we can
        # generate many seeds from it.
        self.base_ctrom = CTRom(rom, ignore_checksum=not is_vanilla)
        self.out_rom = None
        self.has_generated = False

        self.settings = settings
        self.config = config

    # The randomizer will hold onto its last generated rom in self.out_rom
    # The settings and config are made properties so that I can update
    # whether out_rom correctly reflects the settings/config.
    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, new_settings: rset.Settings):
        self._settings = new_settings
        self.has_generated = False

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, new_config: cfg.RandoConfig):
        self._config = new_config
        self.has_generated = False

    # This would be used by a plando to set a non-random config.
    # Should this exist now that config is a property?
    def set_config(self, config: cfg.RandoConfig):
        self.config = config
        # TODO: Are there any sanity checks to apply to the config?

    # Given the settings passed to the randomizer, give the randomizer a
    # random RandoConfig object.
    def set_random_config(self):
        if self.settings is None:
            raise NoSettingsException

        rand.seed(self.settings.seed)

        if rset.GameFlags.MYSTERY in self.settings.gameflags:
            self.settings = mystery.generate_mystery_settings(self.settings)

        # Some of the config defaults (prices, techdb, enemy stats) are
        # read from the rom.  This routine partially patches a copy of the
        # base rom, gets the data, and builds the base config.
        self.config = Randomizer.get_base_config_from_settings(
            bytearray(self.base_ctrom.rom_data.getvalue()),
            self.settings
        )

        # An alternate approach is to build the base config with the pickles
        # provided.  You just have to make sure to redump any time time that
        # patch.ips or hard.ips change.  Below is how you would use pickles.
        '''
        with open('./pickles/default_randoconfig.pickle', 'rb') as infile:
            self.config = pickle.load(infile)

        if self.settings.enemy_difficulty == rset.Difficulty.HARD:
            with open('./pickles/enemy_dict_hard.pickle', 'rb') as infile:
                self.config.enemy_dict = pickle.load(infile)
        '''

        # Character config.  Includes tech randomization.
        charrando.write_pcs_to_config(self.settings, self.config)
        techrandomizer.write_tech_order_to_config(self.settings,
                                                  self.config)

        # Fast Magic.  Should be fine before or after charrando.
        # Safest after.
        fastmagic.write_config(self.settings, self.config)

        # Treasure config.
        treasurewriter.write_treasures_to_config(self.settings, self.config)

        # Enemy rewards
        enemyrewards.write_enemy_rewards_to_config(self.settings, self.config)

        # Key item config.  Important that this goes after treasures because
        # otherwise the treasurewriter can overwrite key items placed by
        # Chronosanity
        logicwriter.commitKeyItems(self.settings, self.config)

        # Now go write LW extra items if need be
        treasurewriter.add_lw_key_item_gear(self.settings, self.config)

        # Shops
        shopwriter.write_shops_to_config(self.settings, self.config)

        # Item Prices
        shopwriter.write_item_prices_to_config(self.settings, self.config)

        # Boss Rando
        bossrando.write_assignment_to_config(self.settings, self.config)

        # This updates the enemy dict in the config with new stats depending
        # on bossrando.write_assignment_to_config().
        bossrando.scale_bosses_given_assignment(self.settings, self.config)

        # Key item Boss scaling (done after boss rando).  Also updates stats.
        bossscaler.set_boss_power(self.settings, self.config)

        # Black Tyrano/Magus boss randomization
        bossrando.randomize_midbosses(self.settings, self.config)

        # Tabs
        tabwriter.write_tabs_to_config(self.settings, self.config)

        # Bucket
        bucketfragment.write_fragments_to_config(self.settings, self.config)

        # Omen elevator
        self.__set_omen_elevators_config()

        # Ice age GG buffs if IA flag is present in settings.
        iceage.write_config(self.settings, self.config)

    def rescale_bosses(self):
        '''Reset enemy stats and redo boss scaling.'''
        if self.settings is None:
            raise NoSettingsException

        if self.config is None:
            raise NoConfigException

        config = self.get_base_config_from_settings(
            self.base_ctrom.rom_data.getbuffer(),
            self.settings
        )

        for loc in self.config.boss_assign_dict:
            boss = self.config.boss_assign_dict[loc]
            scheme = self.config.boss_data_dict[boss].scheme

            for part in set(scheme.ids):
                stats = self.config.enemy_dict[part]
                charm = stats.charm_item
                drop = stats.drop_item

                config.enemy_dict[part].charm_item = charm
                config.enemy_dict[part].drop_item = drop

                self.config.enemy_dict[part] = config.enemy_dict[part]

        bossrando.scale_bosses_given_assignment(self.settings, self.config)
        bossscaler.set_boss_power(self.settings, self.config)

    def __disable_xmenu_charlocks(self, ct_rom):
        '''Ignore the charlock byte when in the X-menu but not Y-menu.'''

        rom = ct_rom.rom_data
        space_man = rom.space_manager

        rt = bytearray.fromhex(
            'AD 36 0D'     # LDA $0D36  [$7E:0D36]  (will be FF in Y-menu, 0 X)
            '10 04'        # BPL foo
            'A9 00'        # LDA #$00 (no charlock byte)
            '80 04'        # BRA bar
            'AF DF 01 7F'  # LDA $7F01DF[$7F:01DF] (charlock byte) [foo]
            '6B'           # RTL [bar]
        )

        start = space_man.get_free_addr(len(rt))
        rom_start = byteops.to_rom_ptr(start)
        rom_start_b = rom_start.to_bytes(3, 'little')
        jsl = b'\x22' + rom_start_b

        rom.seek(0x02CD55)
        rom.write(jsl)

        mark_used = ctevent.FSWriteType.MARK_USED
        rom.seek(start)
        rom.write(rt, mark_used)

    def __set_omen_elevators_config(self):
        '''Determine which omen elevator encounters a seed gets.'''
        # Ruminators, goons, cybots
        fight_thresh_up = [0xA0, 0x60, 0x80]
        fight_thresh_down = [0x80, 0x60, 0xA0]
        fights_up = [ind for ind, thresh in enumerate(fight_thresh_up)
                     if rand.randrange(0, 0x100) < thresh]
        fights_down = [ind for ind, thresh in enumerate(fight_thresh_down)
                       if rand.randrange(0, 0x100) < thresh]

        self.config.omen_elevator_fights_up = fights_up
        self.config.omen_elevator_fights_down = fights_down

    def __set_omen_elevator_ctrom(self, ctrom: CTRom,
                                  fights: list[int],
                                  loc_id: ctenums.LocID):
        '''Write an omen elevator encounters to the rom.'''
        script_man = ctrom.script_manager
        script = script_man.get_script(loc_id)

        start = script.get_function_start(0, 0)
        end = script.get_function_end(0, 0)

        # There are three commands (0x7F) that load a random number.
        # These random numbers are then compared to some thresholds to
        # determine whether a fight occurs.
        pos = start
        for i in range(3):
            pos, cmd = script.find_command([0x7F], pos, end)
            offset = cmd.args[0]

            # Get a val to local mem command
            new_cmd = ctevent.EC.get_blank_command(0x4F)
            new_cmd.args[1] = offset

            # If we determined that fight i should occur, store a 0 to the
            # location that would have held the random number.  It will pass
            # any threshold.  Otherwise, assign 0xFF to fail any threshold.
            if i in fights:
                val = 0
            else:
                val = 0xFF

            new_cmd.args[0] = val

            # delete the get random command.  Put in the val-to-mem command.
            script.delete_commands(pos, 1)
            script.insert_commands(new_cmd.to_bytearray(),  pos)

            pos += len(new_cmd)

    def __set_omen_elevators_ctrom(self, ctrom: CTRom,
                                   config: cfg.RandoConfig):
        '''Set both omen elevators'''
        fights = [config.omen_elevator_fights_down,
                  config.omen_elevator_fights_up]
        loc_ids = [ctenums.LocID.BLACK_OMEN_ELEVATOR_DOWN,
                   ctenums.LocID.BLACK_OMEN_ELEVATOR_UP]

        for x in list(zip(loc_ids, fights)):
            elev_fights = x[1]
            elev_loc_id = x[0]

            self.__set_omen_elevator_ctrom(ctrom, elev_fights, elev_loc_id)

    def __lavos_ngplus(self):
        '''Removes a check for dead Mammon Machine on Lavos NG+'''
        script_man = self.out_rom.script_manager
        script = script_man.get_script(ctenums.LocID.TESSERACT)

        start = script.get_function_start(0, 0)
        end = script.get_function_end(0, 0)

        pos, cmd = script.find_command([0x16], start, end)
        if cmd.args[0:3] == [0xA8, 0x80, 0x86]:
            script.delete_commands(pos, 1)
        else:
            print('failed to find mm flag')

    def __try_mystic_mtn_portal_fix(self):
        '''
        Removes touch == activate from dactyl portal.  Maybe this fixes?
        '''
        loc_id = ctenums.LocID.MYSTIC_MTN_PORTAL
        script = self.out_rom.script_manager.get_script(loc_id)

        EF = ctevent.EF
        EC = ctevent.EC

        # Make a function that's just a return
        func = EF()
        func.add(EC.return_cmd())

        # Set the touch (0x02) function of the portal activation obj (0x0A)
        # to just return.
        script.set_function(0x0A, 0x02, func)

    def __try_proto_dome_fix(self):
        '''Removes touch == activate from proto recruit.  Maybe this fixes?'''
        script_man = self.out_rom.script_manager
        script = script_man.get_script(ctenums.LocID.PROTO_DOME)

        EF = ctevent.EF
        EC = ctevent.EC

        # Make a function that's just a return
        func = EF()
        func.add(EC.return_cmd())

        # Set the touch (0x02) function of the recruit obj (0x18) to the
        # return function.
        script.set_function(0x18, 0x02, func)

    def generate_rom(self):
        '''
        Turns settings + config into self.out_rom.
        '''
        if self.settings is None:
            raise NoSettingsException

        if self.config is None:
            raise NoConfigException

        if self.has_generated:
            return

        # With valid config and settings, we can write generate the rom
        self.__write_out_rom()

    def __write_config_to_out_rom(self):
        '''
        Writes elements of the config to self.out_rom
        '''
        config = self.config
        ctrom = self.out_rom

        # Write enemies out
        for enemy_id, stats in config.enemy_dict.items():
            stats.write_to_stream(ctrom.rom_data, enemy_id)

        # Write treasures out -- this includes key items
        # for treasure in config.treasure_assign_dict.values():
        for tid in config.treasure_assign_dict:
            treasure = config.treasure_assign_dict[tid]
            treasure.write_to_ctrom(ctrom)

        # Write shops out
        config.shop_manager.write_to_ctrom(ctrom)

        # Write prices out
        config.price_manager.write_to_ctrom(ctrom)

        # Write characters out
        # Recruitment spots
        for character in config.char_assign_dict.values():
            character.write_to_ctrom(ctrom)

        # Stats
        config.char_manager.write_stats_to_ctrom(ctrom)

        # Write out the rest of the character data (incl. techs)
        charrando.reassign_characters_on_ctrom(ctrom, config)

        # Write out the bosses and midbossses
        bossrando.write_bosses_to_ctrom(ctrom, config)
        bossrando.write_midbosses_to_ctrom(ctrom, config)

        # tabs
        tabwriter.rewrite_tabs_on_ctrom(ctrom, config)

        # Omen elevator
        self.__set_omen_elevators_ctrom(ctrom, config)

        # Disabling xmenu character locks is only relevant in LoC and IA, but
        # there's no reason not to just do it always.
        self.__disable_xmenu_charlocks(ctrom)

    def __write_out_rom(self):
        '''Given config and settings, write to self.out_rom'''
        self.out_rom = CTRom(self.base_ctrom.rom_data.getvalue(), True)

        # TODO:  Consider working some of the always-applied script changes
        #        Into patch.ips to improve generation speed.
        self.__apply_basic_patches(self.out_rom, self.settings)
        self.__apply_settings_patches(self.out_rom, self.settings)
        self.__apply_cosmetic_patches(self.out_rom, self.settings)

        # This makes copies of heckran cave passagesways, king's trial,
        # and now Zenan Bridge so that all bosses can go there.
        # There's no reason not do just do this regardless of whether
        # boss rando is on.
        bossrando.duplicate_maps_on_ctrom(self.out_rom)
        bossrando.duplicate_zenan_bridge(self.out_rom,
                                         ctenums.LocID.ZENAN_BRIDGE_BOSS)

        # Script changes which can always be made
        Event = ctevent.Event
        script_manager = self.out_rom.script_manager

        # Three dc flag patches can be added regardless.  No reason not to.

        # 1) Set magic learning at game start depending on character assignment
        #    unless LW...because telepod exhibit now has the LW portal change.

        if self.settings.game_mode != rset.GameMode.LOST_WORLDS:
            telepod_event = Event.from_flux('./flux/cr_telepod_exhibit.flux')

            # 3.1.1 Change:
            # The only relevant script change with 3.1.1 is setting the
            # 0x80 bit of 0x7f0057 for the skyway logic in the Telepod
            # Exhibit script.
            EC = ctevent.EC

            # set flag cmd -- too lazy to make an EC function for this
            cmd = EC.generic_two_arg(0x65, 0x07, 0x57)
            start = telepod_event.get_function_start(0x0E, 0x04)
            end = telepod_event.get_function_end(0x0E, 0x04)

            # Set the flag right before the screen darkens
            pos = telepod_event.find_exact_command(EC.fade_screen(),
                                                   start, end)
            telepod_event.insert_commands(cmd.to_bytearray(), pos)

            script_manager.set_script(telepod_event,
                                      ctenums.LocID.TELEPOD_EXHIBIT)
        else:
            # The LW mode sets the magic-learned bits on the load screen.
            # We will just set them all.
            load_screen_event = script_manager.get_script(
                ctenums.LocID.LOAD_SCREEN
                )

            cmd = ctevent.EC.set_bit(0x7F01E0, 0x01)
            pos = load_screen_event.find_exact_command(cmd)

            new_cmd = ctevent.EC.assign_val_to_mem(0x7F, 0x7F01E0, 1)
            load_screen_event.insert_commands(new_cmd.to_bytearray(),
                                              pos)

        # 2) Allows left chest when medal is on non-Frog Frogs
        burrow_event = Event.from_flux('./flux/cr_burrow.Flux')

        # 3) Start Ruins quest when Grand Leon is on non-Frog Frogs
        choras_cafe_event = Event.from_flux('./flux/cr_choras_cafe.Flux')

        script_manager.set_script(burrow_event,
                                  ctenums.LocID.FROGS_BURROW)
        script_manager.set_script(choras_cafe_event,
                                  ctenums.LocID.CHORAS_CAFE)

        # Flag specific script changes:
        #   - Locked characters changes to proto dome and dactyl nest
        #   - Duplicate characters changes to Spekkio when not in LW
        flags = self.settings.gameflags
        mode = self.settings.game_mode
        dup_chars = rset.GameFlags.DUPLICATE_CHARS in flags
        locked_chars = rset.GameFlags.LOCKED_CHARS in flags
        lost_worlds = rset.GameMode.LOST_WORLDS == mode

        if dup_chars and not lost_worlds:
            # Lets Spekkio give magic properly to duplicates
            dc_spekkio_event = Event.from_flux('./flux/charrando-eot.flux')
            script_manager.set_script(dc_spekkio_event,
                                      ctenums.LocID.SPEKKIO)

        if locked_chars:
            lc_dactyl_upper_event = \
                Event.from_flux('./flux/lc_dactyl_upper.Flux')
            script_manager.set_script(lc_dactyl_upper_event,
                                      ctenums.LocID.DACTYL_NEST_UPPER)

            # Note: This changes the Proto Dome script, but it does not change
            #       which objects/functions have the char recruit data, so the
            #       randomization doesn't break.  If a script does change that
            #       data then self.config.char_assign_dict would change.
            # TODO: Just do surgery on the script instead of loading flux.
            lc_proto_dome_event = Event.from_flux('./flux/lc_proto_dome.Flux')
            script_manager.set_script(lc_proto_dome_event,
                                      ctenums.LocID.PROTO_DOME)

        # Proto fix, Mystic Mtn fix, and Lavos NG+ are candidates for being
        # rolled into patch.ips.

        # Two potential softlocks caused by (presumably) touch == activate.
        self.__try_proto_dome_fix()
        self.__try_mystic_mtn_portal_fix()

        # Enable NG+ by defeating Lavos without doing Omen.
        self.__lavos_ngplus()

        # Everything prior was purely based on settings, not the randomization.
        # Now, write the information from the config to the rom.
        self.__write_config_to_out_rom()

        # Ice Age/LoC script changes need to go after the config is written
        # because the recruit spot works by changing all character recruit
        # commands into the recruit's version.  The code inserted by theen
        # recruit locks would get incorrectly changed by this.
        mode = self.settings.game_mode
        if mode == rset.GameMode.ICE_AGE:
            iceage.set_ice_age_recruit_locks(self.out_rom,
                                             self.config)
            iceage.set_ice_age_dungeon_locks(self.out_rom, self.config)
            iceage.set_ending_after_woe(self.out_rom)

        if mode == rset.GameMode.LEGACY_OF_CYRUS:
            legacyofcyrus.write_loc_recruit_locks(self.out_rom,
                                                  self.config)
            legacyofcyrus.write_loc_dungeon_locks(self.out_rom)
            legacyofcyrus.set_ending_after_ozzies_fort(self.out_rom)

        self.out_rom.write_all_scripts_to_rom()
        self.has_generated = True

    def get_generated_rom(self) -> bytearray:
        if not self.has_generated:
            self.generate_rom()

        return self.out_rom.rom_data.getvalue()

    def write_spoiler_log(self, filename):
        with open(filename, 'w') as outfile:
            self.write_settings_spoilers(outfile)
            self.write_tab_spoilers(outfile)
            self.write_key_item_spoilers(outfile)
            self.write_boss_rando_spoilers(outfile)
            self.write_character_spoilers(outfile)
            self.write_boss_stat_spoilers(outfile)
            self.write_treasure_spoilers(outfile)
            self.write_drop_charm_spoilers(outfile)
            self.write_shop_spoilers(outfile)
            self.write_price_spoilers(outfile)

    def write_settings_spoilers(self, file_object):
        file_object.write(f"Game Mode: {self.settings.game_mode}\n")
        file_object.write(f"Enemies: {self.settings.enemy_difficulty}\n")
        file_object.write(f"Items: {self.settings.item_difficulty}\n")
        file_object.write(f"Techs: {self.settings.techorder}\n")
        file_object.write(f"Shops: {self.settings.shopprices}\n")
        file_object.write(f"Flags: {self.settings.gameflags}\n")
        file_object.write(f"Cosmetic: {self.settings.cosmetic_flags}\n\n")

    def write_tab_spoilers(self, file_object):
        file_object.write("Tab Properties\n")
        file_object.write("--------------\n")

        tab_names = [
            'Power Tab',
            'Magic Tab',
            'Speed Tab'
        ]

        tab_magnitudes = [
            self.config.power_tab_amt,
            self.config.magic_tab_amt,
            self.config.speed_tab_amt
        ]

        for i in range(len(tab_names)):
            file_object.write(f'{tab_names[i]}: +{tab_magnitudes[i]}\n')

        file_object.write('\n')

    def write_key_item_spoilers(self, file_object):
        file_object.write("Key Item Locations\n")
        file_object.write("------------------\n")

        # We have to use the logicwriter's Location class only because
        # of Chronosanity's linked locations needing to be handled properly.

        width = max(len(x.getName()) for x in self.config.key_item_locations)

        for location in self.config.key_item_locations:
            file_object.write(str.ljust(f"{location.getName()}", width+8) +
                              str(location.getKeyItem()) + '\n')
        file_object.write('\n')

    def write_character_spoilers(self, file_object):
        char_man = self.config.char_manager
        char_assign = self.config.char_assign_dict

        file_object.write("Character Locations\n")
        file_object.write("-------------------\n")
        for recruit_spot in char_assign.keys():
            held_char = char_assign[recruit_spot].held_char
            reassign_char = \
                self.config.char_manager.pcs[held_char].assigned_char
            file_object.write(str.ljust(f"{recruit_spot}", 20) +
                              f"{char_assign[recruit_spot].held_char}"
                              f" reassigned {reassign_char}\n")
        file_object.write('\n')

        file_object.write("Character Stats\n")
        file_object.write("---------------\n")

        CharID = ctenums.CharID
        dup_chars = rset.GameFlags.DUPLICATE_CHARS in self.settings.gameflags
        techdb = self.config.techdb

        for char_id in range(7):
            file_object.write(f"{CharID(char_id)}:")
            if dup_chars:
                file_object.write(
                    f" assigned to {char_man.pcs[char_id].assigned_char}"
                )
            file_object.write('\n')
            file_object.write(char_man.pcs[char_id].stats.get_stat_string())

            file_object.write('Tech Order:\n')
            for tech_num in range(8):
                tech_id = 1 + 8*char_id + tech_num
                tech = techdb.get_tech(tech_id)
                name = ctstrings.CTString.ct_bytes_to_techname(tech['name'])
                file_object.write(f"\t{name}\n")
            file_object.write('\n')

    def write_treasure_spoilers(self, file_object):
        # Where should the location groupings go?
        width = max(len(str(x))
                    for x in self.config.treasure_assign_dict.keys())

        file_object.write("Treasure Assignment\n")
        file_object.write("-------------------\n")
        treasure_dict = self.config.treasure_assign_dict
        for treasure in treasure_dict.keys():
            file_object.write(str.ljust(str(treasure), width+8) +
                              str(treasure_dict[treasure].held_item) +
                              '\n')
        file_object.write('\n')

    def write_shop_spoilers(self, file_object):
        file_object.write("Shop Assigmment\n")
        file_object.write("---------------\n")
        file_object.write(
            self.config.shop_manager.__str__(self.config.price_manager)
        )
        file_object.write('\n')

    def write_price_spoilers(self, file_object):
        file_object.write("Item Prices\n")
        file_object.write("-----------\n")

        width = max(len(str(x)) for x in list(ctenums.ItemID)) + 8

        item_ids = [x for x in list(ctenums.ItemID)
                    if x in range(1, ctenums.ItemID(0xD0))]

        for item_id in item_ids:
            file_object.write(
                str.ljust(str(ctenums.ItemID(item_id)), width) +
                str(self.config.price_manager.get_price(item_id)) +
                '\n'
            )
        file_object.write('\n')

    def write_boss_rando_spoilers(self, file_object):
        file_object.write("Boss Locations\n")
        file_object.write("--------------\n")

        boss_dict = self.config.boss_assign_dict
        width = max(len(str(x)) for x in boss_dict.keys()) + 8

        for location in boss_dict.keys():
            file_object.write(
                str.ljust(str(location), width) +
                str(boss_dict[location]) +
                '\n'
            )

        file_object.write('\n')

    def write_boss_stat_spoilers(self, file_object):

        scale_dict = self.config.boss_rank
        BossID = ctenums.BossID

        file_object.write("Boss Stats\n")
        file_object.write("----------\n")

        endboss_ids = [
            BossID.LAVOS_SHELL, BossID.INNER_LAVOS, BossID.LAVOS_CORE,
            BossID.ZEAL, BossID.ZEAL_2
        ]

        boss_ids = list(self.config.boss_assign_dict.values()) + \
            [BossID.MAGUS, BossID.BLACK_TYRANO] + endboss_ids

        for boss_id in boss_ids:
            file_object.write(str(boss_id)+':')
            if boss_id in scale_dict.keys():
                file_object.write(
                    f" Key Item scale rank = {scale_dict[boss_id]}"
                )
            if boss_id == BossID.MAGUS:
                file_object.write(
                    f" Assigned {self.config.magus_char}"
                )
            if boss_id == BossID.BLACK_TYRANO:
                file_object.write(
                    f" Element is {self.config.black_tyrano_element}"
                )
            file_object.write('\n')

            boss = self.config.boss_data_dict[boss_id]
            part_ids = list(dict.fromkeys(boss.scheme.ids))
            for part_id in part_ids:
                if len(part_ids) > 1:
                    file_object.write(f"Part: {part_id}\n")
                part_str = str(self.config.enemy_dict[part_id])
                # put the string one tab out
                part_str = '\t' + str.replace(part_str, '\n', '\n\t')
                file_object.write(part_str+'\n')
            file_object.write('\n')

        file_object.write(f"Obstacle is {self.config.obstacle_status}\n\n")

    def write_drop_charm_spoilers(self, file_object):
        file_object.write("Enemy Drop and Charm\n")
        file_object.write("--------------------\n")

        EnTier = enemyrewards.RewardGroup
        get_enemies = enemyrewards.get_enemy_tier
        tiers = [
            get_enemies(EnTier.COMMON_ENEMY),
            get_enemies(EnTier.UNCOMMON_ENEMY),
            get_enemies(EnTier.RARE_ENEMY),
            get_enemies(EnTier.RAREST_ENEMY),
            (
                get_enemies(EnTier.EARLY_BOSS) +
                get_enemies(EnTier.MIDGAME_BOSS) +
                get_enemies(EnTier.LATE_BOSS)
            )
        ]

        labels = ['Common Enemies',
                  'Uncommon Enemies',
                  'Rare Enemies',
                  'Rarest Enemies',
                  'Bosses']

        ids = [x for tier in tiers for x in tier]
        width = max(len(str(x)) for x in ids) + 8

        for ind, tier in enumerate(tiers):
            file_object.write(labels[ind] + '\n')
            for enemy_id in tier:
                file_object.write(
                    '\t' +
                    str.ljust(f"{enemy_id}", width) +
                    " Drop: "
                    f"{self.config.enemy_dict[enemy_id].drop_item}\n")
                file_object.write(
                    '\t' +
                    str.ljust("", width) +
                    "Charm: "
                    f"{self.config.enemy_dict[enemy_id].charm_item}\n")

        file_object.write('\n')

    # Because switching logic is a feature now, we need a settings object.
    # Ugly.  BETA_LOGIC flag is gone now, but keeping it as-is in case of
    # logic changes to test.
    @classmethod
    def __apply_basic_patches(cls, ctrom: CTRom,
                              settings: rset.Settings = None):
        '''Apply patches that are always applied to a jets rom.'''
        rom_data = ctrom.rom_data

        if settings is None:
            # Will give non-beta patch.  Outside of normal randomization,
            # where a settings object is provided, this function is only
            # called for dumping a basic config, and this won't change
            # depending on beta or not.
            settings = rset.Settings.get_race_presets()

        # Apply the patches that always are applied for jets
        # patch.ips makes sure that we have
        #   - Stats/stat growths for characters for CharManager
        #   - Tech data for TechDB
        #   - Item data (including prices) for shops
        # patch_codebase.txt may not be needed
        rom_data.patch_ips_file('./patch.ips')

        # 99.9% sure this patch is redundant now
        rom_data.patch_txt_file('./patches/patch_codebase.txt')

        # I verified that the following convenience patches which are now
        # always applied are disjoint from the glitch fix patches, so it's
        # safe to move them here.
        rom_data.patch_txt_file('./patches/fast_overworld_walk_patch.txt')
        rom_data.patch_txt_file('./patches/faster_epoch_patch.txt')
        rom_data.patch_txt_file('./patches/faster_menu_dpad.txt')

        # It should be safe to move the robo's ribbon code here since it
        # also doesn't depend on flags and should be applied prior to anything
        # else that messes with the items because it shuffles effects
        roboribbon.robo_ribbon_speed(rom_data.getbuffer())

    @classmethod
    def __apply_settings_patches(cls, ctrom: CTRom,
                                 settings: rset.Settings):
        '''Apply patches to a vanilla ctrom based on randomizer settings.  '''
        '''These are patches not handled by writing the config.'''

        rom_data = ctrom.rom_data
        flags = settings.gameflags
        mode = settings.game_mode

        if rset.GameFlags.FIX_GLITCH in flags:
            rom_data.patch_txt_file('./patches/save_anywhere_patch.txt')
            rom_data.patch_txt_file('./patches/unequip_patch.txt')
            rom_data.patch_txt_file('./patches/fadeout_patch.txt')
            rom_data.patch_txt_file('./patches/hp_overflow_patch.txt')

        if rset.GameFlags.QUIET_MODE in flags:
            rom_data.patch_ips_file('./patches/nomusic.ips')

        # TODO:  I'd like to do this with .Flux event changes
        if rset.GameFlags.ZEAL_END in flags:
            rom_data.patch_txt_file('./patches/zeal_end_boss.txt')

        # Patching with lost.ips does not give a valid event for
        # mystic mountains.  I could fix the event by applying a flux file,
        # but I'm worried about what might happen when the invalid event is
        # marked free space.  For now we keep with older versions and apply the
        # mysticmtnfix.ips to restore the event.
        if rset.GameMode.LOST_WORLDS == mode:
            rom_data.patch_ips_file('./patches/lost.ips')
            rom_data.patch_ips_file('./patches/mysticmtnfix.ips')

        if rset.GameFlags.FAST_PENDANT in flags:
            if mode in (rset.GameMode.LOST_WORLDS,
                        rset.GameMode.LEGACY_OF_CYRUS):
                # Game modes where there is no pendant trial need to enforce
                # fast pendant by changing scripts.
                fastpendant.apply_fast_pendant_script(ctrom, settings)
            else:
                rom_data.patch_txt_file('./patches/fast_charge_pendant.txt')

        # Big TODO:  Unwrap the hard patch into its component changes.
        #            As far as I can tell it's just enemies and starting GP.
        if settings.enemy_difficulty == rset.Difficulty.HARD:
            rom_data.patch_ips_file('./patches/hard.ips')

        if rset.GameFlags.VISIBLE_HEALTH in flags:
            qolhacks.force_sightscope_on(ctrom, settings)

        if rset.GameFlags.GUARANTEED_DROPS in flags:
            qolhacks.set_guaranteed_drops(ctrom, settings)

        if rset.GameFlags.UNLOCKED_MAGIC in flags:
            fastmagic.write_ctrom(ctrom, settings)

        if rset.GameFlags.FAST_TABS in flags:
            qolhacks.fast_tab_pickup(ctrom, settings)

        if rset.GameFlags.BUCKET_FRAGMENTS in flags:
            bucketfragment.set_bucket_function(ctrom, settings)
            bucketfragment.set_fragment_properties(ctrom)

    @classmethod
    def __apply_cosmetic_patches(cls, ctrom: CTRom,
                                 settings: rset.Settings):
        cos_flags = settings.cosmetic_flags

        if rset.CosmeticFlags.ZENAN_ALT_MUSIC in cos_flags:
            cosmetichacks.zenan_bridge_alt_battle_music(ctrom, settings)

        if rset.CosmeticFlags.DEATH_PEAK_ALT_MUSIC in cos_flags:
            cosmetichacks.death_peak_singing_mountain_music(ctrom, settings)

    @classmethod
    def dump_default_config(cls, ct_vanilla: bytearray):
        '''Turn vanilla ct rom into default objects for a config.'''
        '''Should run whenever a big patch (patch.ips, hard.ips) changes.'''
        ctrom = CTRom(ct_vanilla, ignore_checksum=False)
        cls.__apply_basic_patches(ctrom)

        RC = cfg.RandoConfig
        config = RC.get_config_from_rom(ctrom.rom_data.getbuffer())

        with open('./pickles/default_randoconfig.pickle', 'wb') as outfile:
            pickle.dump(config, outfile)

    @classmethod
    def get_base_config_from_settings(cls,
                                      ct_vanilla: bytearray,
                                      settings: rset.Settings):
        '''Gets an rset.RandoConfig object with the correct initial values.

        RandoConfig members which are read from rom_data after patches:
          - enemy_dict: holds stats depending on hard mode or not
          - shop_manager: This shouldn't be strictly needed, but at present
                          ShopManager objects read the initial shop data from
                          the rom.
          - price_manager: patch.ips changes the default prices.  Potentially
                           the difficulty patch could too.
          - char_manager: patch.ips changes character stat growths and base
                          stats.
          - techdb: patch.ips changes the basic techs (i.e. Antilife)
        '''

        # It's a little wasteful copying the rom data to partially patch it
        # to extract the base values for the above.

        # I do have a pickle with a default config and normal/hard enemy dicts
        # which can be used instead if this is an issue.  The problem with
        # using those is the need to update them with every patch.
        ctrom = CTRom(ct_vanilla, True)
        Randomizer.__apply_basic_patches(ctrom)

        # Apply hard mode if it's in the settings.
        if settings.enemy_difficulty == rset.Difficulty.HARD:
            ctrom.rom_data.patch_ips_file('./patches/hard.ips')

        config = cfg.RandoConfig.get_config_from_rom(
            bytearray(ctrom.rom_data.getvalue())
        )

        # Fix Falcon Hit to use Spincut as a prerequisite
        techdb = config.techdb
        falcon_hit = techdb.get_tech(ctenums.TechID.FALCON_HIT)
        falcon_hit['lrn_req'][0] = int(ctenums.TechID.SPINCUT)
        techdb.set_tech(falcon_hit, ctenums.TechID.FALCON_HIT)

        # Make X-Strike use Spincut+Leapslash
        if rset.GameFlags.BUFF_XSTRIKE in settings.gameflags:
            techdb = config.techdb
            x_strike = techdb.get_tech(ctenums.TechID.X_STRIKE)
            x_strike['control'][5] = int(ctenums.TechID.SPINCUT)
            x_strike['control'][6] = int(ctenums.TechID.LEAP_SLASH)

            # Crono's techlevel = 4 (spincut)
            # Frog's techlevel = 5 (leapslash)
            x_strike['lrn_req'] = [4, 5, 0xFF]

            x_strike['mmp'][0] = int(ctenums.TechID.SPINCUT)
            x_strike['mmp'][1] = int(ctenums.TechID.LEAP_SLASH)
            techdb.set_tech(x_strike, ctenums.TechID.X_STRIKE)

        if rset.GameFlags.AYLA_REBALANCE in settings.gameflags:
            # Apply Ayla Changes
            combo_tripkick_effect_id = 0x3D
            rock_tech_effect_id = int(ctenums.TechID.ROCK_THROW)

            techdb = config.techdb
            effects = techdb.effects
            power_byte = 9

            # Triple Kick combo power set to 0x2B=43 to match single tech power
            trip_pwr = combo_tripkick_effect_id*techdb.effect_size + power_byte
            effects[trip_pwr] = 0x2B

            # Rock throw getting the 15% boost that single tech tripkick got
            # From 0x1E=30 to 0x23=35
            rock_pwr = rock_tech_effect_id*techdb.effect_size + power_byte
            effects[rock_pwr] = 0x23

        return config

    @classmethod
    def get_randmomized_rom(cls,
                            rom: bytearray,
                            settings: rset.Settings) -> bytearray:
        rando = Randomizer(rom, settings)
        rando.set_random_config()
        rando.generate_rom()
        return rando.get_generated_rom()


def read_names():
    p = open("names.txt", "r")
    names = p.readline()
    names = names.split(",")
    p.close()
    return names


#
# Handle the command line interface for the randomizer.
#
def generate_from_command_line():

    sourcefile, outputfolder = get_input_file_from_command_line()

    # note ext contains the '.'
    _, ext = os.path.splitext(sourcefile)

    with open(sourcefile, 'rb') as infile:
        rom = infile.read()

    if not CTRom.validate_ct_rom_bytes(rom):
        print(
            'Warning: File provided is not a vanilla CT ROM.  Proceed '
            'anyway?  Randomization is likely to fail. (Y/N)'
        )
        proceed = (input().upper() == 'Y')

        if not proceed:
            raise SystemExit()

    settings = get_settings_from_command_line()
    rando = Randomizer(rom, is_vanilla=False,
                       settings=settings,
                       config=None)

    rando.set_random_config()
    out_rom = rando.get_generated_rom()

    base_name = os.path.basename(sourcefile)
    flag_string = settings.get_flag_string()
    out_name = f"{base_name}.{flag_string}.{settings.seed}{ext}"
    out_path = os.path.join(outputfolder, out_name)

    with open(out_path, 'wb') as outfile:
        outfile.write(out_rom)

    print(f"generated: {out_path}")


def get_input_file_from_command_line() -> (str, str):
    sourcefile = input("Please enter ROM name or drag it onto the screen.")

    # When dragging, bash puts \' around the path.  Remove if present.
    quotes = ('\'', '\"')
    print(sourcefile[0], sourcefile[-2])
    if sourcefile[0] in quotes and sourcefile[-2] in quotes:
        sourcefile = sourcefile[1:-2]

    _, extension = os.path.splitext(sourcefile)

    if not os.path.isfile(sourcefile):
        input("Error: File does not exist.")
        exit()

    print(extension)
    if extension not in ('.sfc', '.smc'):
        input(
            "Invalid File Name. "
            "Try placing the ROM in the same folder as the randomizer. "
            "Also, try writing the extension(.sfc/smc)."
        )
        exit()

    # In theory ask for alternate output folder, but for now just place in
    # the same one.
    outputfolder = os.path.dirname(sourcefile)
    print(
        "The output ROM will be placed in the same folder:"
        f"\n\t{outputfolder}"
    )

    return sourcefile, outputfolder


def get_settings_from_command_line() -> rset.Settings:
    settings = rset.Settings()
    settings.gameflags = rset.GameFlags(False)

    seed = input(
            "Enter seed(or leave blank if you want to randomly generate one)."
    )
    if seed is None or seed == "":
        names = read_names()
        seed = "".join(rand.choice(names) for i in range(2))

    settings.seed = seed

    # Difficulty (now separated between item/enemy but only in gui)
    difficulty = input("Choose your difficulty \nEasy(e)/Normal(n)/Hard(h) ")
    difficulty = difficulty.lower()
    if difficulty == "n":
        settings.item_difficulty = rset.Difficulty.NORMAL
        settings.enemy_difficulty = rset.Difficulty.NORMAL
    elif difficulty == "e":
        settings.item_difficulty = rset.Difficulty.EASY
        settings.enemy_difficulty = rset.Difficulty.NORMAL
    elif difficulty == 'h':
        settings.item_difficulty = rset.Difficulty.HARD
        settings.enemy_difficulty = rset.Difficulty.HARD
    else:
        print('Invalid selection.  Defaulting to normal')
        settings.item_difficulty = rset.Difficulty.NORMAL
        settings.enemy_difficulty = rset.Difficulty.NORMAL

    glitch_fixes = input(
        "Would you like to disable (most known) glitches(g)? Y/N "
    )
    glitch_fixes = glitch_fixes.upper()
    if glitch_fixes == "Y":
        settings.gameflags |= rset.GameFlags.FIX_GLITCH

    lost_worlds = input("Would you want to activate Lost Worlds(l)? Y/N ")
    lost_worlds = lost_worlds.upper()
    if lost_worlds == "Y":
        settings.game_mode = rset.GameMode.LOST_WORLDS

    boss_scaler = input(
        "Do you want bosses to scale with progression(b)? Y/N "
    )
    boss_scaler = boss_scaler.upper()
    if boss_scaler == "Y":
        settings.gameflags |= rset.GameFlags.BOSS_SCALE

    boss_rando = input("Do you want randomized bosses(ro)? Y/N ")
    boss_rando = boss_rando.upper()
    if boss_rando == "Y":
        settings.gameflags |= rset.GameFlags.BOSS_RANDO

    zeal_end = input(
        "Would you like Zeal 2 to be a final boss? "
        "Note that defeating Lavos still ends the game(z). Y/N "
    )
    zeal_end = zeal_end.upper()
    if zeal_end == "Y":
        settings.gameflags |= rset.GameFlags.ZEAL_END

    if lost_worlds == "Y":
        # At the moment, LW is not compatible with fast pendant
        pass
    else:
        quick_pendant = input(
            "Do you want the pendant to be charged upon entering the "
            "future(p)? Y/N "
        )
        quick_pendant = quick_pendant.upper()
        if quick_pendant == "Y":
            settings.gameflags |= rset.GameFlags.FAST_PENDANT

    locked_chars = input(
        "Do you want characters to be further locked(c)? Y/N "
    )
    locked_chars = locked_chars.upper()
    if locked_chars == "Y":
        settings.gameflags |= rset.GameFlags.LOCKED_CHARS

    tech_list = input("Do you want to randomize techs(te)? Y/N ")
    tech_list = tech_list.upper()
    if tech_list == "Y":
        settings.techorder = rset.TechOrder.FULL_RANDOM
        tech_list_balanced = input(
            "Do you want tech order randomziation to be biased so that "
            "less useful techs are more likely to appear earlier in the "
            "tech list (tex)? Y/N "
        )
        tech_list_balanced = tech_list_balanced.upper()
        if tech_list_balanced == "Y":
            settings.techorder = rset.TechOrder.BALANCED_RANDOM
    else:
        settings.techorder = rset.TechOrder.NORMAL

    unlocked_magic = input(
        "Do you want the ability to learn all techs without visiting "
        "Spekkio(m)? Y/N "
    )
    unlocked_magic = unlocked_magic.upper()
    if unlocked_magic == "Y":
        settings.gameflags |= rset.GameFlags.UNLOCKED_MAGIC

    quiet_mode = input("Do you want to enable quiet mode (No music)(q)? Y/N ")
    quiet_mode = quiet_mode.upper()
    if quiet_mode == "Y":
        settings.gameflags |= rset.GameFlags.QUIET_MODE

    chronosanity = input(
        "Do you want to enable Chronosanity "
        "(key items can appear in chests)? (cr)? Y/N "
    )
    chronosanity = chronosanity.upper()
    if chronosanity == "Y":
        settings.gameflags |= rset.GameFlags.CHRONOSANITY

    duplicate_chars = input("Do you want to allow duplicte characters? ")
    duplicate_chars = duplicate_chars.upper()
    if duplicate_chars == "Y":
        settings.gameflags |= rset.GameFlags.DUPLICATE_CHARS
        same_char_techs = input(
            "Should duplicate characters learn dual techs? Y/N "
        ).upper()
        if same_char_techs == 'Y':
            settings.dc_settings.duplicate_duals = True

    tab_treasures = input("Do you want all treasures to be tabs(tb)? Y/N ")
    tab_treasures = tab_treasures.upper()
    if tab_treasures == "Y":
        settings.gameflags |= rset.GameFlags.TAB_TREASURES

    shop_prices = input(
        "Do you want shop prices to be Normal(n), Free(f), Mostly Random(m), "
        "or Fully Random(r)? "
    )
    shop_prices = shop_prices.upper()
    if shop_prices == "F":
        settings.shopprices = rset.ShopPrices.FREE
    elif shop_prices == "M":
        settings.shopprices = rset.ShopPrices.MOSTLY_RANDOM
    elif shop_prices == "R":
        settings.shopprices = rset.ShopPrices.FULLY_RANDOM
    elif shop_prices == 'N':
        settings.shopprices = rset.ShopPrices.NORMAL
    else:
        print('Invalid Entry.  Defaulting to Normal prices.')
        settings.shopprices = rset.ShopPrices.NORMAL

    return settings


def test_json():
    with open('./roms/ct.sfc', 'rb') as infile:
        rom = infile.read()

    settings = rset.Settings.get_race_presets()
    settings.seed = 'asdfasf'

    rando = Randomizer(rom, is_vanilla=True,
                       settings=settings,
                       config=None)
    rando.set_random_config()
    rando.config.to_json('./json/json_test.json')


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "-c":
        generate_from_command_line()
    else:
        print("Please run randomizergui.py for a graphical interface. \n"
              "Either randomizer.py or randomizergui.py can be run with the "
              "-c option to use\nthe command line.")


if __name__ == "__main__":
    main()
