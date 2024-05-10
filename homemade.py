"""
Some example classes for people who want to create a homemade bot.

With these classes, bot makers will not have to implement the UCI or XBoard interfaces themselves.
"""

from __future__ import annotations
import chess
from chess.engine import PlayResult, Limit
import random
from lib.engine_wrapper import MinimalEngine, MOVE, COMMANDS_TYPE, OPTIONS_TYPE
from typing import Any
import logging

import socket
import chess.engine
import chess.polyglot
import chess.syzygy
import chess.gaviota
import chess
from lib import model
from lib.config import Configuration
from typing import Optional

from server.utils import send_dict, recv_dict
from modeling.data import Game
from server.utils import SYSTEMS, DEFAULT_SYSTEM

# Use this logger variable to print messages to the console or log files.
# logger.info("message") will always print "message" to the console or log file.
# logger.debug("message") will only print "message" if verbose logging is enabled.
logger = logging.getLogger(__name__)


class ExampleEngine(MinimalEngine):
    """An example engine that all homemade engines inherit."""

    pass


# Bot names and ideas from tom7's excellent eloWorld video


class RandomMove(ExampleEngine):
    """Get a random move."""

    def search(self, board: chess.Board, *args: Any) -> PlayResult:
        """Choose a random move."""
        return PlayResult(random.choice(list(board.legal_moves)), None)


class Alphabetical(ExampleEngine):
    """Get the first move when sorted by san representation."""

    def search(self, board: chess.Board, *args: Any) -> PlayResult:
        """Choose the first move alphabetically."""
        moves = list(board.legal_moves)
        moves.sort(key=board.san)
        return PlayResult(moves[0], None)


class FirstMove(ExampleEngine):
    """Get the first move when sorted by uci representation."""

    def search(self, board: chess.Board, *args: Any) -> PlayResult:
        """Choose the first move alphabetically in uci representation."""
        moves = list(board.legal_moves)
        moves.sort(key=str)
        return PlayResult(moves[0], None)



class LMEngine(MinimalEngine):
    def __init__(
        self,
        commands: COMMANDS_TYPE,
        options: OPTIONS_TYPE,
        stderr: Optional[int],
        draw_or_resign: Configuration,
        game: Optional[model.Game] = None,
        name: Optional[str] = None,
        **popen_args: str,
    ) -> None:
        super().__init__(
            commands, options, stderr, draw_or_resign, game, name, **popen_args
        )
        system_alias = options.get("system_alias", None)
        if system_alias is None:
            self.system = DEFAULT_SYSTEM
        else:
            assert system_alias in SYSTEMS
            self.system = SYSTEMS[system_alias]

        if game is None:
            self.game_info = {}
        else:
            opponent_elo = game.opponent.rating
            self.game_info = {
                "time_control": f"{game.clock_initial.seconds}+{game.clock_increment.seconds}",
                "white_elo": None,
                "black_elo": None,
            }
            if game.is_white:
                self.game_info["black_elo"] = opponent_elo
            else:
                self.game_info["white_elo"] = opponent_elo

    def search(
        self,
        board: chess.Board,
        time_limit: Limit,
        ponder: bool,
        draw_offered: bool,
        root_moves: MOVE,
    ) -> PlayResult:
        """
        Choose a move using multiple different methods.

        :param board: The current position.
        :param time_limit: Conditions for how long the engine can search (e.g. we have 10 seconds and search up to depth 10).
        :param ponder: Whether the engine can ponder after playing a move.
        :param draw_offered: Whether the bot was offered a draw.
        :param root_moves: If it is a list, the engine should only play a move that is in `root_moves`.
        :return: The move to play.
        """
        port = self.system.port
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect(("localhost", port))
        logger.info(f"listening on port {port}")
        game = Game(
            self.game_info["time_control"],
            self.game_info["white_elo"],
            self.game_info["black_elo"],
            None,
            False,
            [m.uci() for m in board.move_stack],
            [0] * len(board.move_stack),
        )
        logger.info(f"sent {game.to_dict()}")
        send_dict(conn, game.to_dict())
        data = recv_dict(conn)
        logger.info(f"received {data}")
        resigned = data.get("resigned", False)
        if data.get("think_time") is not None:
            info = {"think_time": data["think_time"]}
        else:
            info = {}
        return PlayResult(chess.Move.from_uci(data["move"]), None, resigned=resigned, info=info)
