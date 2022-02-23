from __future__ import annotations

import typing

import random
import randosettings as rset


def random_weighted_choice_from_dict(choice_dict: dict[typing.Any, int]):
    keys, weights = zip(*choice_dict.items())
    return random.choices(keys, weights, k=1)[0]


def generate_mystery_settings(base_settings: rset.Settings) -> rset.Settings:

    if rset.GameFlags.MYSTERY not in base_settings.gameflags:
        return base_settings

    GF = rset.GameFlags
    ret_settings = rset.Settings()

    ret_flags = GF(0)
    qol_cosm_options = [GF.FAST_TABS, GF.VISIBLE_HEALTH,
                        GF.FAST_PENDANT, GF.ZEAL_END,
                        GF.QUIET_MODE, GF.FIX_GLITCH,
                        GF.DUPLICATE_TECHS, GF.BUFF_XSTRIKE,
                        GF.GUARANTEED_DROPS, GF.AYLA_REBALANCE]

    # Set the qol flags specified in base settings
    for x in qol_cosm_options:
        if x in base_settings.gameflags:
            ret_flags |= x

    weighted_choice = random_weighted_choice_from_dict
    ms = base_settings.mystery_settings

    ret_settings.game_mode = weighted_choice(ms.game_mode_freqs)
    ret_settings.item_difficulty = weighted_choice(ms.item_difficulty_freqs)
    ret_settings.enemy_difficulty = weighted_choice(ms.enemy_difficulty_freqs)
    ret_settings.techorder = weighted_choice(ms.tech_order_freqs)
    ret_settings.shopprices = weighted_choice(ms.shop_price_freqs)

    # Now Flags
    force_disabled_flags = rset.get_forced_off(ret_settings.game_mode)
    force_enabled_flags = rset.get_forced_on(ret_settings.game_mode)

    # Order is important in that some flags block off others.
    # Really, once game mode is determined, it's just chronosanity that
    # blocks off boss scaling.
    flags = [GF.TAB_TREASURES, GF.BUCKET_FRAGMENTS, GF.CHRONOSANITY,
             GF.BOSS_RANDO, GF.UNLOCKED_MAGIC,
             GF.BOSS_SCALE, GF.LOCKED_CHARS, GF.DUPLICATE_CHARS]

    for flag in flags:
        added_flag = GF(0)
        if flag in force_disabled_flags:
            added_flag = GF(0)
        elif flag in force_enabled_flags:
            added_flag = flag
        elif flag in ms.flag_prob_dict:
            prob = ms.flag_prob_dict[flag]
            if random.random() < prob:
                added_flag = flag
            else:
                added_flag = GF(0)

        if added_flag == flag:
            force_disabled_flags |= rset.get_forced_off(flag)
            force_enabled_flags |= rset.get_forced_on(flag)
            ret_flags |= flag

    ret_flags |= GF.MYSTERY

    ret_settings.cosmetic_flags = base_settings.cosmetic_flags
    ret_settings.gameflags = ret_flags
    ret_settings.tab_settings = base_settings.tab_settings
    ret_settings.ro_settings = base_settings.ro_settings
    ret_settings.char_choices = base_settings.char_choices

    return ret_settings
