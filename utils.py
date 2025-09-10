from lib.conversation import Conversation
import json
from dataclasses import dataclass


@dataclass
class User:
    user_id: str
    games: list[str]
    system_order: list[str]


def say_welcome(conversation: Conversation, opponent: str) -> None:
    admin = "@yimingz3"
    welcome_msgs = [
        f"Hello {opponent}!",
        "You are playing against Allie, a chessbot who tries her best to play the same way a human player would."
    ]

    for msg in welcome_msgs:
        conversation.send_message("player", msg)


def send_survey(conversation: Conversation, game_id: str) -> None:
    survey_msgs = [
        "Thanks for playing!",
        "We would really appreciate your feedback of our system through a survey, which should take around a minute.",
        f"If you are interested, please copy the game ID {game_id} and fill out [forms.gle/AeBMxvkxui92Kuiq9].",
    ]

    for msg in survey_msgs:
        conversation.send_message("player", msg)
