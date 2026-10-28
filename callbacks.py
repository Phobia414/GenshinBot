from aiogram.filters.callback_data import CallbackData


class MenuCB(CallbackData, prefix="menu"):
    action: str
    owner_id: int

class RegionCB(CallbackData, prefix="reg"):
    region: str
    owner_id: int

class CharCB(CallbackData, prefix="char"):
    character: str
    owner_id: int

class TaskCB(CallbackData, prefix="task"):
    task_id: str
    owner_id: int

class ShopCB(CallbackData, prefix="shop"):
    item: str
    owner_id: int

class ProposeCB(CallbackData, prefix="prop"):
    action: str
    proposer_id: int
    target_id: int

class RelCB(CallbackData, prefix="rel"):
    action: str
    owner_id: int

class GiftCB(CallbackData, prefix="gift"):
    item: str
    owner_id: int

class GuildCB(CallbackData, prefix="guild"):
    action: str
    owner_id: int
    guild_id: int = 0

class FunCB(CallbackData, prefix="fun"):
    action: str
    owner_id: int

class CasinoCB(CallbackData, prefix="cas"):
    game: str
    bet: int
    owner_id: int

class QuizCB(CallbackData, prefix="quiz"):
    answer: int
    correct: int
    owner_id: int

class DuelCB(CallbackData, prefix="duel"):
    action: str
    challenger_id: int
    target_id: int
    bet: int

class ArtCB(CallbackData, prefix="art"):
    action: str
    owner_id: int

class ArtifactCB(CallbackData, prefix="artf"):
    action: str
    art_id: int
    owner_id: int

class TopCB(CallbackData, prefix="top"):
    action: str
    owner_id: int

class DungeonCB(CallbackData, prefix="dun"):
    action: str
    dungeon: str
    owner_id: int

class CookCB(CallbackData, prefix="cook"):
    action: str
    recipe: str
    owner_id: int

class ListsCB(CallbackData, prefix="lists"):
    action: str
    owner_id: int

class CmdCatCB(CallbackData, prefix="cmd"):
    cat: str
    owner_id: int

class BossCB(CallbackData, prefix="boss"):
    action: str
    owner_id: int

class GachaInvCB(CallbackData, prefix="ginv"):
    action: str
    item_id: int = 0
    rarity: int = 0  # <--- ДОБАВЛЕНО ДЛЯ МАССОВОЙ ПРОДАЖИ
    owner_id: int = 0