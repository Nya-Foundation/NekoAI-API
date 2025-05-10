from enum import Enum


class DirectorTools(Enum):
    LINEART = "lineart"
    SKETCH = "sketch"
    BACKGROUND_REMOVAL = "bg-removal"
    EMOTIOIN = "emotion"
    DECLUTTER = "declutter"
    COLORIZE = "colorize"


class EmotionOptions(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SCARED = "scared"
    SURPRISED = "surprised"
    TIRED = "tired"
    EXCITED = "excited"
    NERVOUS = "nervous"
    THINKING = "thinking"
    CONFUSED = "confused"
    SHY = "shy"
    DISGUSTED = "disgusted"
    SMUG = "smug"
    BORED = "bored"
    LAUGHING = "laughing"
    IRRITATED = "irritated"
    AROUSED = "aroused"
    EMBARRASSED = "embarrassed"
    WORRIED = "worried"
    LOVE = "love"
    DETERMINED = "determined"
    HURT = "hurt"
    PLAYFUL = "playful"


class EmotionLevel(Enum):
    NORMAL = 0
    SLIGHTLY_WEAK = 1
    WEAK = 2
    EVEN_WEAKER = 3
    VERY_WEAK = 4
    WEAKEST = 5
