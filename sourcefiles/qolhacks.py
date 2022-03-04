# File for quality of life hacks

import ctevent
import ctenums

from ctrom import CTRom
import randoconfig as cfg
import randosettings as rset


class ScriptTabTreasure(cfg.ScriptTreasure):
    '''ScriptTreasure with extra method for removing exploremode offs.'''

    def remove_pause(self, ctrom: CTRom):
        '''
        Removes the exploremode off/on from the script.  Moves the pickup
        flag before the textbox if needed.
        '''

        script = ctrom.script_manager.get_script(self.location)
        start = script.get_function_start(self.object_id, self.function_id)
        end = script.get_function_end(self.object_id, self.function_id)

        pos = start
        num_removed = 0
        while True:
            # exploremode toggle commands are 0xE3.  We're nuking them
            pos, _ = script.find_command([0xE3], start, end)

            if pos is None:
                break

            script.delete_commands(pos, 1)
            num_removed += 1

        # print(f"Num removed: {num_removed}")
        if num_removed % 2 != 0:
            # This is not a reliable indicator.  The 'PartyFollow' command can
            # also undo 'ExploreMode Off' as in the Magus Castle Dungeons.
            # print("Warning: Removed an odd number of exploremode commands")
            # input()
            pass

        # Now make sure that the flag set is after the textbox.  Otherwise
        # it's possible to pick the same tab up multiple times.

        # Bit setting is in command 0x65
        pos_flag, flag_cmd = script.find_command([0x65], start, end)

        # 0xBB, 0xC1, 0xC2 are the basic textbox commands
        pos_text, text_cmd = script.find_command([0xBB, 0xC1, 0xC2],
                                                 start, end)

        if pos_flag is None or pos_text is None:
            print(f'Error finding flag set or text box in {self.location}')
            raise SystemExit

        # If the item looted flag is set after the texbox, then the player
        # can keep the textbox up, leave the screen, and avoid setting the
        # flag, so the tab can be picked up again.
        if pos_flag > pos_text:
            # In this case, put the flag right before the item is added.
            pos_add_item, _ = script.find_command([0xCA], start, end)

            script.delete_commands(pos_flag, 1)
            script.insert_commands(flag_cmd.to_bytearray(), pos_add_item)


# Toma's grave's speed tab is annoying because the same function covers
# the pop turn-in and the speed tab.
# We need to
#  1) Remove the exploremode off from the start of the function
#  2) Add an exploremode on command after checking for pop, etc
#  3) Pray calling exploremode on when it's already on doesn't break things.
class TomasGraveTreasure(ScriptTabTreasure):

    def remove_pause(self, ctrom: CTRom):

        script = ctrom.script_manager.get_script(self.location)
        start = script.get_function_start(self.object_id, self.function_id)
        end = script.get_function_end(self.object_id, self.function_id)

        pos = start

        # remove initial exploremode off
        if script.data[pos] == 0xE3:
            script.delete_commands(pos, 1)
        else:
            print("Error: Couldn't find initial exploremode command.")
            exit()

        # insert an exploremode off after checks for pop
        # marker is scrollscreen (0xE7) 00 00
        scroll_screen = ctevent.EC.generic_two_arg(0xE7, 0, 0)
        pos = script.find_exact_command(scroll_screen, pos, end)

        if pos is None:
            print("Error: couldn't find scroll screen")
            exit()

        explore_off = ctevent.EC.generic_one_arg(0xE3, 0)
        script.insert_commands(explore_off.to_bytearray(), pos)


# Trick the game into thinking P1 has the SightScope equipped, for enemy health
# to always be visible.
def force_sightscope_on(ctrom: CTRom, settings: rset.Settings):
    if rset.GameFlags.VISIBLE_HEALTH in settings.gameflags:
        # Seek to the location in the ROM after the game checks if P1's
        # accessory is a SightScope
        ctrom.rom_data.seek(0x0CF039)
        # Ignore the result of that comparison and evaluate to always true, by
        # overwriting the BEQ (branch-if-equal) to BRA (branch-always)
        ctrom.rom_data.write(bytes([0x80]))


def fast_tab_pickup(ctrom: CTRom, settings: rset.Settings):

    if rset.GameFlags.FAST_TABS not in settings.gameflags:
        return

    TID = ctenums.TreasureID
    LocID = ctenums.LocID
    ItemID = ctenums.ItemID

    # Eventually, this might make it into a part of the randoconfig.
    # For now, the held_item and such don't matter.  We just want the
    # location, object, function to nuke the exploremode commands.
    slow_tabs = {
        TID.GUARDIA_FOREST_POWER_TAB_600: ScriptTabTreasure(
            location=LocID.GUARDIA_FOREST_600,
            object_id=0x3F,
            function_id=0x01,
            item_num=0,
            held_item=ItemID.POWER_TAB
        ),
        TID.GUARDIA_FOREST_POWER_TAB_1000: ScriptTabTreasure(
            location=LocID.GUARDIA_FOREST_1000,
            object_id=0x26,
            function_id=0x01,
            item_num=1,
            held_item=ItemID.POWER_TAB
        ),
        TID.PORRE_MARKET_600_POWER_TAB: ScriptTabTreasure(
            location=LocID.PORRE_MARKET_600,
            object_id=0x0C,
            function_id=0x01,
            item_num=1,
            held_item=ItemID.POWER_TAB
        ),
        TID.MANORIA_CONFINEMENT_POWER_TAB: ScriptTabTreasure(
            location=LocID.MANORIA_CONFINEMENT,
            object_id=0x0A,
            function_id=0x01,
            item_num=0,
            held_item=ItemID.POWER_TAB
        ),
        TID.TOMAS_GRAVE_SPEED_TAB: TomasGraveTreasure(
            location=LocID.WEST_CAPE,
            object_id=0x08,
            function_id=0x01,
            item_num=0,
            held_item=ItemID.SPEED_TAB
        ),
        TID.DENADORO_MTS_SPEED_TAB: ScriptTabTreasure(
            location=LocID.DENADORO_WEST_FACE,
            object_id=0x09,
            function_id=0x01,
            item_num=0,
            held_item=ItemID.SPEED_TAB
        ),
        TID.GIANTS_CLAW_CAVERNS_POWER_TAB: ScriptTabTreasure(
            location=LocID.GIANTS_CLAW_CAVERNS,
            object_id=0x0D,
            function_id=0x01,
            item_num=0,
            held_item=ItemID.POWER_TAB
        ),
        TID.GIANTS_CLAW_ENTRANCE_POWER_TAB: ScriptTabTreasure(
            location=LocID.GIANTS_CLAW_ENTRANCE,
            object_id=0x0B,
            function_id=0x01,
            item_num=0,
            held_item=ItemID.POWER_TAB
        ),
        TID.GIANTS_CLAW_TRAPS_POWER_TAB: ScriptTabTreasure(
            location=LocID.ANCIENT_TYRANO_LAIR_TRAPS,
            object_id=0x15,
            function_id=0x01,
            item_num=0,
            held_item=ItemID.POWER_TAB
        ),
        TID.MAGUS_CASTLE_DUNGEONS_MAGIC_TAB: ScriptTabTreasure(
            location=LocID.MAGUS_CASTLE_DUNGEONS,
            object_id=0x08,
            function_id=0x01,
            item_num=0,
            held_item=ItemID.MAGIC_TAB
        ),
        TID.MAGUS_CASTLE_FLEA_MAGIC_TAB: ScriptTabTreasure(
            location=LocID.MAGUS_CASTLE_FLEA,
            object_id=0x0D,
            function_id=0x01,
            item_num=0,
            held_item=ItemID.SPEED_TAB
        ),
        TID.ARRIS_DOME_SEALED_POWER_TAB: ScriptTabTreasure(
            location=LocID.ARRIS_DOME_SEALED_ROOM,
            object_id=0x08,
            function_id=0x01,
            item_num=0,
            held_item=ItemID.SPEED_TAB
        ),
        TID.TRANN_DOME_SEALED_MAGIC_TAB: ScriptTabTreasure(
            location=LocID.TRANN_DOME_SEALED_ROOM,
            object_id=0x08,
            function_id=0x01,
            item_num=0,
            held_item=ItemID.SPEED_TAB
        )
    }

    for tab in slow_tabs:
        # print(f"Made {tab} fast.")
        slow_tabs[tab].remove_pause(ctrom)


def set_guaranteed_drops(ctrom: CTRom, settings: rset.Settings):
    if rset.GameFlags.GUARANTEED_DROPS not in settings.gameflags:
        return

    # If charm == drop, item drops are guaranteed.  However, when the
    # charm and drop are different, there is a chance of no drop.
    # It looks like CT checks (random_num % 100) <= 90
    # The check is:
    # $FD/AC27 C9 5A       CMP #$5A
    # $FD/AC29 B0 20       BCS $20
    # Note BCS will branch when the value in >= 0x5A
    # I don't think it works out to exactly 90% chance of a drop because the
    # random numbers look to be random in [0, 0xFF].  So it's actually a bit
    # higher than 90%.

    # Changing 0x5A = 90 to 0x64 = 100 would do it
    # But let's go for overkill and make it 0xFF.
    rom = ctrom.rom_data
    rom.seek(0x3DAC28)
    rom.write(bytes([0xFF]))


# After writing additional hacks, put them here. Based on the settings, they
# will or will not modify the ROM.
def attempt_all_qol_hacks(ctrom: CTRom, settings: rset.Settings):
    force_sightscope_on(ctrom, settings)
    fast_tab_pickup(ctrom, settings)
    set_guaranteed_drops(ctrom, settings)
