from __future__ import annotations
from ctenums import EnemyID, TreasureID as TID, LocID, ItemID, \
    RecruitID, CharID

from enemystats import EnemyStats
import logicfactory
import logicwriter_chronosanity as logicwriter

import randoconfig as cfg
import randosettings as rset

# Order of stats:
# HP, Level, Magic, Magic Def, Off, Def, XP, GP, TP
# Sometimes xp, gp, tp are omitted at the end.
scaling_data = {
    EnemyID.RUST_TYRANO: [[6000, 16, 16, 50, 160, 127, 3000, 4000, 50],
                          [7000, 20, 20, 50, 170, 127, 3500, 6000, 60],
                          [8000, 30, 30, 50, 180, 127, 4000, 8000, 70]],
    EnemyID.DRAGON_TANK: [[1100, 15, 15, 60, 50, 160, 1600, 2500, 26],
                          [1300, 30, 30, 60, 100, 160, 2200, 4000, 36],
                          [1300, 30, 30, 60, 100, 160, 2200, 4000, 36]],
    EnemyID.TANK_HEAD: [[1400, 20, 20, 60, 50, 160],
                        [1600, 30, 30, 60, 50, 160],
                        [1600, 30, 30, 60, 50, 160]],
    EnemyID.GRINDER: [[1400, 20, 20, 60, 50, 160],
                      [1600, 30, 30, 60, 50, 160],
                      [1600, 30, 30, 60, 50, 160]],
    EnemyID.SON_OF_SUN_EYE: [["", 20, 20, "", "", "", 1600, 3000, 30],
                             ["", 30, 20, "", "", "", 2200, 5000, 40],
                             ["", 30, 30, "", "", "", 2800, 7000, 50]],
    EnemyID.SON_OF_SUN_FLAME: [["", 20, 20, "", "", ""],
                               ["", 30, 20, "", "", ""],
                               ["", 30, 30, "", "", ""]],
    EnemyID.NIZBEL: [[6000, 20, 20, 60, 155, 253, 4000, 4400, 45],
                     [7000, 30, 30, 60, 175, 253, 5000, 5500, 55],
                     [8000, 40, 40, 65, 190, 253, 6000, 6800, 65]],
    EnemyID.RETINITE_TOP: [[2000, 15, 15, 60, 130, 153, 1200, 0, 12],
                           [2200, 20, 20, 65, 160, 165, 1400, 0, 14],
                           [2400, 25, 25, 70, 190, 178, 1600, 0, 16]],
    EnemyID.RETINITE_BOTTOM: [[2000, 15, 15, 60, 130, 153, 1200, 0, 12],
                              [2200, 20, 20, 65, 160, 165, 1400, 0, 14],
                              [2400, 25, 25, 70, 190, 178, 1600, 0, 16]],
    # Should the eye get less hp with higher scaling?
    EnemyID.RETINITE_EYE: [[700, 15, 19, 60, 50, 153, 2400, 2100, 30],
                           [800, 15, 19, 65, 50, 165, 2800, 2700, 40],
                           [900, 15, 19, 70, 50, 178, 3200, 3300, 50]],
    EnemyID.YAKRA_XIII: [[5200, 17, 18, 50, 95, 127, 2800, 3000, 50],
                         [5800, 17, 18, 50, 120, 127, 3400, 4000, 60],
                         [6300, 17, 18, 50, 150, 127, 4000, 5000, 70]],
    EnemyID.GUARDIAN: [[3500, 15, 15, 50, 16, 127, 2500, 3000, 30],
                       [4000, 20, 20, 50, 16, 127, 3000, 4000, 40],
                       [4300, 30, 30, 50, 16, 127, 3500, 5000, 50]],
    EnemyID.GUARDIAN_BIT: [[500, 12, 12, 50, 32, 127],
                           [500, 15, 15, 50, 50, 127],
                           [500, 17, 17, 50, 74, 127]],
    EnemyID.MOTHERBRAIN: [[3500, 20, 20, 50, 100, 127, 3100, 4000, 50],
                          [4000, 30, 30, 50, 100, 127, 3700, 5000, 60],
                          [4500, 40, 40, 50, 100, 127, 4300, 6000, 70]],
    EnemyID.DISPLAY: [[1, 15, 15, 50, 144, 127],
                      [1, 15, 20, 50, 144, 127],
                      [1, 15, 25, 50, 144, 127]],
    EnemyID.R_SERIES: [[1200, 15, 15, 50, 52, 127, 500, 400, 10],
                       [1400, 20, 20, 50, 75, 127, 600, 600, 15],
                       [1200, 15, 15, 50, 52, 127, 500, 400, 10]],
    EnemyID.GIGA_GAIA_HEAD: [[8000, 32, 15, 50, 50, 127, 5000, 7000, 90],
                             [9000, 32, 15, 50, 50, 127, 6000, 8100, 100],
                             [10000, 32, 15, 50, 50, 127, 7000, 9200, 110]],
    EnemyID.GIGA_GAIA_LEFT: [[2500, 20, 30, 61, 40, 127],
                             [3000, 30, 30, 61, 40, 127],
                             [3500, 40, 30, 61, 40, 127]],
    EnemyID.GIGA_GAIA_RIGHT: [[2500, 20, 30, 50, 60, 158],
                              [3000, 30, 30, 50, 60, 158],
                              [3500, 40, 30, 50, 60, 158]]
}


# TODO: Separate determining rank from setting power.  Maybe the rank can be
#       stored in the config and then written out later.
def set_boss_power(settings: rset.Settings, config: cfg.RandoConfig):
    # First, boss scaling only works for normal logic
    chronosanity = rset.GameFlags.CHRONOSANITY in settings.gameflags
    lost_worlds = settings.game_mode == rset.GameMode.LOST_WORLDS
    boss_scaling = rset.GameFlags.BOSS_SCALE in settings.gameflags

    if not boss_scaling:
        return

    if chronosanity or lost_worlds:
        print('Boss scaling not compatible with either Lost Worlds or '
              'Chronosanity.  Returning.')
        return

    game_config = logicfactory.getGameConfig(settings, config)
    key_item_list = game_config.keyItemList

    # To match the original implementation, make a dict with
    # ItemID --> TreasureID  for key items
    key_item_dict = {config.treasure_assign_dict[loc].held_item: loc
                     for loc in config.treasure_assign_dict.keys()
                     if config.treasure_assign_dict[loc].held_item
                     in key_item_list}

    boss_rank = dict()
    boss_assign = config.boss_assign_dict

    # Treasure --> Location of Boss
    # This gives the location of the boss to scale when the treasure location
    # holds a key item.
    # Note:  Locations open at the start of the game (Denadoro, Bridge,
    #        Heckran) are never scaled, even if they have top rank items.
    loc_dict: dict[TID, LocID] = {
        TID.REPTITE_LAIR_KEY: LocID.REPTITE_LAIR_AZALA_ROOM,
        TID.KINGS_TRIAL_KEY: LocID.KINGS_TRIAL_NEW,
        TID.GIANTS_CLAW_KEY: LocID.GIANTS_CLAW_TYRANO,
        TID.FIONA_KEY: LocID.SUNKEN_DESERT_DEVOURER,
        TID.MT_WOE_KEY: LocID.MT_WOE_SUMMIT,
    }

    # Treasure --> Item prerequisite
    # This gives the item to add to the important_keys pool when the treasure
    # location holds a key item.
    # TODO:  Automate this somehow in the logic object.
    item_req_dict: dict[TID, ItemID] = {
        TID.REPTITE_LAIR_KEY: ItemID.GATE_KEY,
        TID.KINGS_TRIAL_KEY: ItemID.PRISMSHARD,
        TID.GIANTS_CLAW_KEY: ItemID.TOMAS_POP,
        TID.FROGS_BURROW_LEFT: ItemID.HERO_MEDAL
    }

    no_req_tids = [TID.DENADORO_MTS_KEY, TID.ZENAN_BRIDGE_KEY,
                   TID.SNAIL_STOP_KEY, TID.LAZY_CARPENTER,
                   TID.TABAN_KEY]

    rank = 3
    important_keys = [ItemID.C_TRIGGER, ItemID.CLONE, ItemID.RUBY_KNIFE]

    while rank > 0:
        # print(f"rank = {rank}")
        # print(important_keys)
        important_tids = [key_item_dict[item] for item in important_keys]

        for item in important_keys:
            # print(f"{item} is in {key_item_dict[item]}")
            pass

        important_keys = list()

        for tid in important_tids:
            if tid in [TID.SUN_PALACE_KEY, TID.ARRIS_DOME_KEY,
                       TID.GENO_DOME_KEY]:
                # If you found an important item in the future:
                #   1) Set prison boss (dtank) to rank-1 if not already ranked
                #   2) Set all future bosses to rank
                # This only happens once, for the highest ranked item in the
                # future.  Lower rank items found in the future will not
                # decrease the rank of the future bosses.
                if ItemID.PENDANT not in important_keys:
                    important_keys.append(ItemID.PENDANT)
                # print(f"Adding {ItemID.PENDANT} to important keys")
                prisonboss = boss_assign[LocID.PRISON_CATWALKS]

                # Skip rank assignment if dtank already has a higher rank.
                # This will happen if keys of multiple levels are in future.
                if prisonboss not in boss_rank.keys() or (
                        prisonboss in boss_rank.keys() and
                        boss_rank[prisonboss] < rank
                ):
                    boss_rank[prisonboss] = rank - 1

                # There is a bug in previous implementations where the future
                # bosses were also only ranked if dtank was not already ranked.
                # In the case that Melchior's item changes dtank's rank, the
                # future bosses would never be ranked.

                # The original intention was to rank the future bosses based on
                # the highest ranked item there.  We'll preserve this.

                # All future bosses have the same rank, so just pick Arris.
                arrisboss = boss_assign[LocID.ARRIS_DOME_GUARDIAN_CHAMBER]
                if arrisboss not in boss_rank or boss_rank[arrisboss] < rank:
                    future_locs = [LocID.SUN_PALACE,
                                   LocID.GENO_DOME_MAINFRAME,
                                   LocID.ARRIS_DOME_GUARDIAN_CHAMBER]
                    for loc in future_locs:
                        futureboss = boss_assign[loc]
                        # print(f"Setting {futureboss} to rank {rank}")
                        boss_rank[futureboss] = rank
            elif tid == TID.MELCHIOR_KEY:
                # When Melchior gets a key item:
                #  1) gate key and pendant get added for next rank
                #  2) king's trial boss gets set to rank
                #  3) prison boss (dtank) gets set to rank-1
                # This is subtle:  Dtank's rank can not be decreased by future
                # locations holding items of lower rank, but it will be reduced
                # by Melchior having a lower rank item.
                for item in (ItemID.GATE_KEY, ItemID.PENDANT):
                    if item not in important_keys:
                        important_keys.append(item)

                trialboss = boss_assign[LocID.KINGS_TRIAL_NEW]
                boss_rank[trialboss] = rank

                prisonboss = boss_assign[LocID.PRISON_CATWALKS]
                boss_rank[prisonboss] = rank-1

            else:
                # Other TIDs are straightforward.  Add their prerequisite item
                # to the important_keys pool if they have one.  Rank their
                # boss if they have one.
                if tid in loc_dict.keys():
                    location = loc_dict[tid]
                    boss = boss_assign[location]
                    boss_rank[boss] = rank
                    # print(f"Setting {boss} to rank {rank}")

                if tid in item_req_dict.keys():
                    item = item_req_dict[tid]
                    important_keys.append(item)
                    # print(f"Adding {item} to important keys")

                if (
                        tid not in loc_dict.keys() and
                        tid not in item_req_dict.keys() and
                        tid not in no_req_tids
                ):
                    print(f"Warning: {tid} not in either dictionary")
                    input()

        # Really, this just happens on the first iteration of the loop.
        if rank > 2:
            important_keys.extend([ItemID.BENT_HILT,
                                   ItemID.BENT_SWORD,
                                   ItemID.DREAMSTONE])

        important_keys = list(set(important_keys))
        rank -= 1

    char_dict = config.char_assign_dict
    proto_char = char_dict[RecruitID.PROTO_DOME].held_char
    factoryboss = boss_assign[LocID.FACTORY_RUINS_SECURITY_CENTER]

    if rset.GameFlags.LOCKED_CHARS in settings.gameflags:
        if proto_char in [CharID.ROBO, CharID.AYLA]:
            boss_rank[factoryboss] = 1
        elif proto_char in [CharID.CRONO, CharID.MAGUS]:
            boss_rank[factoryboss] = 2

    config.boss_rank = boss_rank

    for boss in boss_rank.keys():
        # print(f"{boss} has rank {boss_rank[boss]}")
        boss_data = config.boss_data_dict[boss]
        part_ids = list(set(boss_data.scheme.ids))
        rank = boss_rank[boss]

        for part in part_ids:
            if part in scaling_data.keys():
                stat_list = scaling_data[part][rank-1]
                # print(f"{part} has defined stats {stat_list}")
            else:
                # When there is no bespoke stat scaling, fall back to each
                # rank adding X% over the previous rank.
                stats = config.enemy_dict[part]
                stat_list = rank_up_stats(stats, rank)
                # print(f"{part} gets computed stats {stat_list}")

            config.enemy_dict[part].replace_from_stat_list(stat_list)


# Just add 15% with each rank up.
# TODO: This doesn't give you what you want.  The scaled stats are supposed
#       to start at hard mode stats I think?  Maybe this needs to start by
#       loading up the hard-mode stats (from a pickle?) and then scaling.
def rank_up_stats(stats: EnemyStats, rank: int) -> list[int]:
    scale_factor = 1.15 ** rank
    orig_mdef = stats.mdef
    orig_def = stats.defense

    stat_list = [stats.hp, stats.level, stats.magic,
                 stats.mdef, stats.offense, stats.defense,
                 stats.xp, stats.gp, stats.tp]

    stat_max = [0x7FFF, 0xFF, 0xFF,
                0xFF, 0xFF, 0xFF,
                0xFFFF, 0xFFFF, 0xFF]

    stat_list = [int(min(stat_list[i]*scale_factor, stat_max[i]))
                 for i in range(len(stat_list))]

    # set mdef/def back to normal range
    stat_list[3] = orig_mdef
    stat_list[5] = orig_def

    return stat_list
