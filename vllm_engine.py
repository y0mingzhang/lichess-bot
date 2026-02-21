"""VLLM Chess Engine for lichess-bot using HTTP API."""

import logging
import os
import sys
import time

import chess
import requests
from chess.engine import Limit, PlayResult

# Add the project root to sys.path so we can import from src
project_root = os.path.join(os.path.dirname(__file__), "../..")
sys.path.insert(0, project_root)

from lib import model
from lib.config import Configuration
from lib.engine_wrapper import COMMANDS_TYPE, OPTIONS_TYPE, MinimalEngine
from lib.lichess_types import MOVE

from data.tokenizer import Tokenizer, build_game_prompt
from data.tokens import TerminationTokens

logger = logging.getLogger(__name__)

VLLM_RETRIES = 5
VLLM_TIMEOUT = 30


class VLLMEngine(MinimalEngine):
    """Chess engine using VLLM HTTP API for move prediction."""

    _base_logit_bias: dict[int, float] = {i: -100.0 for i in range(Tokenizer.vocab_size())}

    def __init__(
        self,
        commands: COMMANDS_TYPE,
        options: OPTIONS_TYPE,
        stderr: int | None,
        draw_or_resign: Configuration,
        game: model.Game | None = None,
        name: str | None = None,
        **popen_args: str,
    ) -> None:
        super().__init__(commands, options, stderr, draw_or_resign, game, name, **popen_args)
        port = os.environ.get("VLLM_PORT", 8000)
        self.api_url = f"http://localhost:{port}/v1/completions"
        self.model_name = os.environ.get("VLLM_MODEL", "")
        self.game = game
        if game is None:
            self.game_info = {
                "seconds_per_side": "300",
                "increment": "0",
            }
            self.target_elo = 1500
            self.opponent_elo = 1500
            self.bot_is_white = True
        else:
            self.game_info = {
                "seconds_per_side": str(int(game.clock_initial.total_seconds())),
                "increment": str(int(game.clock_increment.total_seconds())),
            }
            self.opponent_elo = game.opponent.rating
            self.target_elo = game.opponent.rating
            self.bot_is_white = game.is_white

    def search(
        self,
        board: chess.Board,
        time_limit: Limit,
        ponder: bool,
        draw_offered: bool,
        root_moves: MOVE,
    ) -> PlayResult:
        legal_moves = list(board.legal_moves)
        if isinstance(root_moves, list):
            legal_moves = [move for move in legal_moves if move in root_moves]

        logit_bias = self._base_logit_bias.copy()
        for move in legal_moves:
            logit_bias[Tokenizer.token_to_idx[f"<move:{move.uci()}>"]] = 0.0
        logit_bias[Tokenizer.token_to_idx[TerminationTokens.NORMAL_TERMINATION.value]] = 0.0

        if self.bot_is_white:
            white_elo, black_elo = self.target_elo, self.opponent_elo
        else:
            white_elo, black_elo = self.opponent_elo, self.target_elo

        prompt = build_game_prompt(
            self.game_info["seconds_per_side"],
            self.game_info["increment"],
            white_elo,
            black_elo,
            [m.uci() for m in board.move_stack],
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": 1,
            "temperature": 1.0,
            "logit_bias": logit_bias,
        }

        for attempt in range(VLLM_RETRIES):
            try:
                response = requests.post(self.api_url, json=payload, timeout=VLLM_TIMEOUT)
                response.raise_for_status()
                result = response.json()
                break
            except (requests.RequestException, ValueError) as e:
                if attempt == VLLM_RETRIES - 1:
                    logger.error(f"vLLM failed after {VLLM_RETRIES} attempts: {e}")
                    return PlayResult(None, None, resigned=True)
                logger.warning(f"vLLM attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(2**attempt)

        token_str = result["choices"][0]["text"].strip()
        if token_str == TerminationTokens.NORMAL_TERMINATION.value:
            return PlayResult(None, None, resigned=True)

        return PlayResult(Tokenizer.extract_move_from_move_token(token_str), None)
