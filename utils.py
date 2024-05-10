from lib.conversation import Conversation
import json
from dataclasses import dataclass
import redis

with open("/home/yimingz3/secrets/redis-auth") as f:
    redis_pw = f.read()
r = redis.Redis(host="localhost", port=13498, decode_responses=True, password=redis_pw)


@dataclass
class User:
    user_id: str
    games: list[str]
    system_order: list[str]


def write_user(user: User) -> bool:
    return r.set(f"user:{user.user_id}", json.dumps(user.__dict__))


def read_user(user_id: str) -> User:
    user_string = r.get(f"user:{user_id}")

    if user_string is None:
        return User(user_id, [], [])

    user = User(**json.loads(user_string))
    return user


def say_welcome(conversation: Conversation, opponent: str, user: User) -> None:
    admin = "AllieTheChessBot" + "@" + "gmail.com"
    welcome_msgs = [
        f"Hello {opponent}! Thanks for participating in this study.",
        "You are playing against Allie, a chessbot who tries her best to play the same way a human player would.",
        "After your game session, please take a minute to fill out our survey.",
        "Also, please try to play at least 3 games, as we change Allie's configuration between games.",
        f"If you have questions or feedback, please send a message to [{admin}].",
    ]

    for msg in welcome_msgs:
        conversation.send_message("player", msg)


def send_survey(conversation: Conversation, game_id: str) -> None:
    survey_msgs = [
        "Thanks for completing this game.",
        "We would really appreciate your feedback of our system through a survey, which should take around a minute.",
        f"If you are interested, please copy the game ID {game_id} and fill out [forms.gle/AeBMxvkxui92Kuiq9].",
    ]

    for msg in survey_msgs:
        conversation.send_message("player", msg)
