from __future__ import annotations
from enum import Flag, IntEnum, auto
from dataclasses import dataclass, field
from typing import Union

import ctenums


class StrIntEnum(IntEnum):

    def __str__(self):
        x = self.__repr__().split('.')[1].split(':')[0].lower().capitalize()
        x = x.replace('_', ' ')
        return x

    @classmethod
    def str_dict(cls) -> dict:
        return dict((x, str(x)) for x in list(cls))

    @classmethod
    def inv_str_dict(cls) -> dict:
        return dict((str(x), x) for x in list(cls))


class GameMode(StrIntEnum):
    STANDARD = auto()
    LOST_WORLDS = auto()
    ICE_AGE = auto()
    LEGACY_OF_CYRUS = auto()
    VANILLA_RANDO = auto()


class Difficulty(StrIntEnum):
    EASY = 0
    NORMAL = 1
    HARD = 2


class TechOrder(StrIntEnum):
    NORMAL = 0
    FULL_RANDOM = 1
    BALANCED_RANDOM = 2


class ShopPrices(StrIntEnum):
    NORMAL = 0
    MOSTLY_RANDOM = 1
    FULLY_RANDOM = 2
    FREE = 3


class GameFlags(Flag):
    FIX_GLITCH = auto()
    BOSS_SCALE = auto()
    ZEAL_END = auto()
    FAST_PENDANT = auto()
    LOCKED_CHARS = auto()
    UNLOCKED_MAGIC = auto()
    CHRONOSANITY = auto()
    TAB_TREASURES = auto()  # Maybe needs to be part of treasure page?
    BOSS_RANDO = auto()
    DUPLICATE_CHARS = auto()
    DUPLICATE_TECHS = auto()
    VISIBLE_HEALTH = auto()
    FAST_TABS = auto()
    BUCKET_FRAGMENTS = auto()
    BUFF_XSTRIKE = auto()
    MYSTERY = auto()
    AYLA_REBALANCE = auto()
    BOSS_SIGHTSCOPE = auto()
    BLACKHOLE_REWORK = auto()
    ROBO_REWORK = auto()
    HEALING_ITEM_RANDO = auto()
    FREE_MENU_GLITCH = auto()
    GEAR_RANDO = auto()
    FIRST_TWO = auto()
    EPOCH_FAIL = auto()
    MARLE_REWORK = auto()
    BOSS_SPOT_HP = auto()

# Dictionary for what flags force what other flags off.
# Note that this is NOT symmetric.  For example Lost Worlds will force
# Boss Scaling off, but not vice versa because it's annoying to have to
# click off every minor flag to select a major flag like a game mode.
_GF = GameFlags
_GM = GameMode
_forced_off_dict: dict[Union[_GF, _GM], _GF] = {
    _GF.FIX_GLITCH: _GF(0),
    _GF.BOSS_SCALE: _GF(0),
    _GF.ZEAL_END: _GF(0),
    _GF.FAST_PENDANT: _GF(0),
    _GF.LOCKED_CHARS: _GF(0),
    _GF.UNLOCKED_MAGIC: _GF(0),
    _GF.CHRONOSANITY: _GF.BOSS_SCALE,
    _GF.TAB_TREASURES: _GF(0),
    _GF.BOSS_RANDO: _GF(0),
    _GF.DUPLICATE_CHARS: _GF(0),
    _GF.DUPLICATE_TECHS: _GF(0),
    _GF.VISIBLE_HEALTH: _GF(0),
    _GF.FAST_TABS: _GF(0),
    _GF.BUCKET_FRAGMENTS: _GF(0),
    _GF.BUFF_XSTRIKE: _GF(0),
    _GF.MYSTERY: _GF(0),
    _GF.GEAR_RANDO: _GF(0),
    _GF.HEALING_ITEM_RANDO: _GF(0),
    _GF.EPOCH_FAIL: _GF(0),
    _GM.STANDARD: _GF(0),
    _GM.LOST_WORLDS: _GF.BOSS_SCALE | _GF.BUCKET_FRAGMENTS,
    _GM.ICE_AGE: (
        _GF.ZEAL_END |
        _GF.BOSS_SCALE | _GF.BUCKET_FRAGMENTS
    ),
    _GM.LEGACY_OF_CYRUS: (
        _GF.ZEAL_END |
        _GF.BUCKET_FRAGMENTS |
        _GF.BOSS_RANDO | _GF.BOSS_SCALE | _GF.BOSS_RANDO
    ),
    _GM.VANILLA_RANDO: (
        _GF.BOSS_SCALE | 
        _GF.BUFF_XSTRIKE | _GF.BUCKET_FRAGMENTS | _GF.AYLA_REBALANCE |
        _GF.BLACKHOLE_REWORK | _GF.MARLE_REWORK | _GF.ROBO_REWORK
    )
}


# Similar dictionary for forcing flags on
_forced_on_dict = {
    _GF.FIX_GLITCH: _GF(0),
    _GF.BOSS_SCALE: _GF(0),
    _GF.ZEAL_END: _GF(0),
    _GF.FAST_PENDANT: _GF(0),
    _GF.LOCKED_CHARS: _GF(0),
    _GF.UNLOCKED_MAGIC: _GF(0),
    _GF.CHRONOSANITY: _GF(0),
    _GF.TAB_TREASURES: _GF(0),
    _GF.BOSS_RANDO: _GF(0),
    _GF.DUPLICATE_CHARS: _GF(0),
    _GF.DUPLICATE_TECHS: _GF(0),
    _GF.VISIBLE_HEALTH: _GF(0),
    _GF.FAST_TABS: _GF(0),
    _GF.BUCKET_FRAGMENTS: _GF(0),
    _GF.BUFF_XSTRIKE: _GF(0),
    _GF.MYSTERY: _GF(0),
    _GF.GEAR_RANDO: _GF(0),
    _GF.HEALING_ITEM_RANDO: _GF(0),
    _GF.EPOCH_FAIL: _GF(0),
    _GM.STANDARD: _GF(0),
    _GM.LOST_WORLDS: _GF.UNLOCKED_MAGIC,
    _GM.ICE_AGE: _GF.UNLOCKED_MAGIC,
    _GM.LEGACY_OF_CYRUS: _GF.UNLOCKED_MAGIC,
    _GM.VANILLA_RANDO: _GF(0)
}


def get_forced_off(flag: GameFlags) -> GameFlags:
    return _forced_off_dict.get(flag, GameFlags(0))


def get_forced_on(flag: GameFlags) -> GameFlags:
    return _forced_on_dict.get(flag, GameFlags(0))


class CosmeticFlags(Flag):
    ZENAN_ALT_MUSIC = auto()
    DEATH_PEAK_ALT_MUSIC = auto()
    QUIET_MODE = auto()


class TabRandoScheme(StrIntEnum):
    UNIFORM = 0
    BINOMIAL = 1


@dataclass
class TabSettings:
    scheme: TabRandoScheme = TabRandoScheme.UNIFORM
    binom_success: float = 0.5  # Only used by binom if set
    power_min: int = 2
    power_max: int = 4
    magic_min: int = 1
    magic_max: int = 3
    speed_min: int = 1
    speed_max: int = 1


@dataclass
class ROSettings:
    loc_list: list[ctenums.BossID] = field(default_factory=list)
    boss_list: list[ctenums.BossID] = field(default_factory=list)
    preserve_parts: bool = False


@dataclass
class BucketSettings:
    num_fragments: int = 15
    needed_fragments: int = 10


class MysterySettings:
    def __init__(self):
        self.game_mode_freqs: dict[GameMode, int] = {
            GameMode.STANDARD: 75,
            GameMode.LOST_WORLDS: 25,
            GameMode.LEGACY_OF_CYRUS: 0,
            GameMode.ICE_AGE: 0,
            GameMode.VANILLA_RANDO: 0
        }
        self.item_difficulty_freqs: dict[Difficulty, int] = {
            Difficulty.EASY: 15,
            Difficulty.NORMAL: 70,
            Difficulty.HARD: 15
        }
        self.enemy_difficulty_freqs: dict[Difficulty, int] = {
            Difficulty.NORMAL: 75,
            Difficulty.HARD: 25
        }
        self.tech_order_freqs: dict[TechOrder, int] = {
            TechOrder.NORMAL: 10,
            TechOrder.BALANCED_RANDOM: 10,
            TechOrder.FULL_RANDOM: 80
        }
        self.shop_price_freqs: dict[ShopPrices, int] = {
            ShopPrices.NORMAL: 70,
            ShopPrices.MOSTLY_RANDOM: 10,
            ShopPrices.FULLY_RANDOM: 10,
            ShopPrices.FREE: 10
        }
        self.flag_prob_dict: dict[GameFlags, float] = {
            GameFlags.TAB_TREASURES: 0.10,
            GameFlags.UNLOCKED_MAGIC: 0.5,
            GameFlags.BUCKET_FRAGMENTS: 0.15,
            GameFlags.CHRONOSANITY: 0.50,
            GameFlags.BOSS_RANDO: 0.50,
            GameFlags.BOSS_SCALE: 0.10,
            GameFlags.LOCKED_CHARS: 0.25,
            GameFlags.DUPLICATE_CHARS: 0.25,
            GameFlags.EPOCH_FAIL: 0.5,
            GameFlags.GEAR_RANDO: 0.25,
            GameFlags.HEALING_ITEM_RANDO: 0.25
        }

    def __str__(self):
        ret_str = ''
        ret_str += str(self.game_mode_freqs) + '\n'
        ret_str += str(self.item_difficulty_freqs) + '\n'
        ret_str += str(self.enemy_difficulty_freqs) + '\n'
        ret_str += str(self.tech_order_freqs) + '\n'
        ret_str += str(self.shop_price_freqs) + '\n'
        ret_str += str(self.flag_prob_dict) + '\n'

        return ret_str


class Settings:

    def __init__(self):

        self.game_mode = GameMode.STANDARD
        self.item_difficulty = Difficulty.NORMAL
        self.enemy_difficulty = Difficulty.NORMAL

        self.techorder = TechOrder.FULL_RANDOM
        self.shopprices = ShopPrices.NORMAL

        self.mystery_settings = MysterySettings()

        self.gameflags = GameFlags(0)
        self.char_choices = [[i for i in range(7)] for j in range(7)]

        BossID = ctenums.BossID
        boss_list = \
            BossID.get_one_part_bosses() + BossID.get_two_part_bosses()

        boss_list += [BossID.SON_OF_SUN, BossID.RETINITE,
                      BossID.MOTHER_BRAIN, BossID.GIGA_GAIA,
                      BossID.GUARDIAN]

        loc_list = ctenums.LocID.get_boss_locations()

        self.ro_settings = ROSettings(loc_list, boss_list, False)
        self.bucket_settings = BucketSettings()

        self.tab_settings = TabSettings()
        self.cosmetic_flags = CosmeticFlags(0)
        self.seed = ''

        self.char_names: list[str] = [
            'Crono', 'Marle', 'Lucca', 'Robo', 'Frog', 'Ayla', 'Magus',
            'Epoch'
        ]

    def _jot_json(self):
        return {
            "seed": self.seed,
            "mode": str(self.game_mode),
            "enemy_difficulty": str(self.enemy_difficulty),
            "item_difficulty": str(self.item_difficulty),
            "tech_order": str(self.techorder),
            "shops": str(self.shopprices),
            "flags": self.gameflags,
            "cosmetic_flags": self.cosmetic_flags
        }

    def get_race_presets():
        ret = Settings()

        ret.item_difficulty = Difficulty.NORMAL
        ret.enemy_difficulty = Difficulty.NORMAL

        ret.shopprices = ShopPrices.NORMAL
        ret.techorder = TechOrder.FULL_RANDOM

        ret.gameflags = (GameFlags.FIX_GLITCH |
                         GameFlags.FAST_PENDANT |
                         GameFlags.ZEAL_END)

        ret.seed = ''

        return ret

    def get_new_player_presets():
        ret = Settings()

        ret.item_difficulty = Difficulty.EASY
        ret.enemy_difficulty = Difficulty.NORMAL

        ret.shopprices = ShopPrices.NORMAL
        ret.techorder = TechOrder.FULL_RANDOM

        ret.gameflags = (GameFlags.FIX_GLITCH |
                         GameFlags.FAST_PENDANT |
                         GameFlags.ZEAL_END |
                         GameFlags.UNLOCKED_MAGIC |
                         GameFlags.VISIBLE_HEALTH |
                         GameFlags.FAST_TABS)

        ret.seed = ''

        return ret

    def get_lost_worlds_presets():
        ret = Settings()

        ret.game_mode = GameMode.LOST_WORLDS
        ret.item_difficulty = Difficulty.NORMAL
        ret.enemy_difficulty = Difficulty.NORMAL

        ret.shopprices = ShopPrices.NORMAL
        ret.techorder = TechOrder.FULL_RANDOM

        ret.gameflags = (GameFlags.FIX_GLITCH | GameFlags.ZEAL_END)

        ret.seed = ''
        return ret

    def get_hard_presets():
        ret = Settings()

        ret.item_difficulty = Difficulty.HARD
        ret.enemy_difficulty = Difficulty.HARD

        ret.shopprices = ShopPrices.NORMAL
        ret.techorder = TechOrder.BALANCED_RANDOM

        ret.gameflags = (GameFlags.FIX_GLITCH |
                         GameFlags.BOSS_SCALE |
                         GameFlags.LOCKED_CHARS)

        ret.seed = ''
        return ret

    def get_flag_string(self):
        # Flag string is based only on main game flags and game mode

        diff_str_dict = {
            Difficulty.EASY: 'e',
            Difficulty.NORMAL: 'n',
            Difficulty.HARD: 'h',
        }

        tech_str_dict = {
            TechOrder.FULL_RANDOM: 'te',
            TechOrder.BALANCED_RANDOM: 'tex',
            TechOrder.NORMAL: ''
        }

        game_mode_dict = {
            GameMode.STANDARD: 'st',
            GameMode.LOST_WORLDS: 'lw',
            GameMode.ICE_AGE: 'ia',
            GameMode.LEGACY_OF_CYRUS: 'loc',
            GameMode.VANILLA_RANDO: 'van'
        }

        flag_str_dict = {
            GameFlags.FIX_GLITCH: 'g',
            GameFlags.BOSS_SCALE: 'b',
            GameFlags.BOSS_RANDO: 'ro',
            GameFlags.ZEAL_END: 'z',
            GameFlags.FAST_PENDANT: 'p',
            GameFlags.LOCKED_CHARS: 'c',
            GameFlags.UNLOCKED_MAGIC: 'm',
            GameFlags.CHRONOSANITY: 'cr',
            GameFlags.TAB_TREASURES: 'tb',
            GameFlags.DUPLICATE_CHARS: 'dc',
        }

        shop_str_dict = {
            ShopPrices.FREE: 'spf',
            ShopPrices.MOSTLY_RANDOM: 'spm',
            ShopPrices.FULLY_RANDOM: 'spr',
            ShopPrices.NORMAL: ''
        }

        if GameFlags.MYSTERY in self.gameflags:
            flag_string = 'mystery'
        else:
            # Now we have difficulty for enemies and items separated, but to
            # match the old flag string, just use enemy difficulty.
            # This won't match for easy, since there's no easy enemy
            # difficulty.
            flag_string = ''
            flag_string += (game_mode_dict[self.game_mode] + '.')
            flag_string += diff_str_dict[self.enemy_difficulty]

            # Add the item difficulty if it differs
            # (old 'e' will end up as 'ne')
            if self.item_difficulty != self.enemy_difficulty:
                flag_string += diff_str_dict[self.item_difficulty]

            for flag in flag_str_dict:
                if flag in self.gameflags:
                    flag_string += flag_str_dict[flag]

            flag_string += tech_str_dict[self.techorder]
            flag_string += shop_str_dict[self.shopprices]

        return flag_string
