"""Perft: count the leaf nodes of the legal move tree to verify move generation.

Usage (from the repository root):
    python tests/perft.py          # check all positions and measure the speed
    python tests/perft.py --hash   # also check the incremental Zobrist hash (slower)
"""

import sys
import time

from raychess.board import STARTING_FEN, Board, move_to_uci
from raychess.movegen import generate_legal_moves

# (name, FEN, depth, expected nodes) from https://www.chessprogramming.org/Perft_Results
POSITIONS = [
    ("start", STARTING_FEN, 4, 197_281),
    (
        "kiwipete",
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        3,
        97_862,
    ),
    ("position 3", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 5, 674_624),
    (
        "position 4",
        "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
        4,
        422_333,
    ),
    (
        "position 4 mirrored",
        "r2q1rk1/pP1p2pp/Q4n2/bbp1p3/Np6/1B3NBn/pPPP1PPP/R3K2R b KQ - 0 1",
        4,
        422_333,
    ),
    (
        "position 5",
        "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
        3,
        62_379,
    ),
    (
        "position 6",
        "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
        3,
        89_890,
    ),
]


def perft(board: Board, depth: int, check_hash: bool = False) -> int:
    """Number of leaf nodes of the legal move tree of the given depth."""
    if check_hash and board.key != board.compute_key():
        raise AssertionError(f"Zobrist hash mismatch in position {board.to_fen()}")
    if depth == 0:
        return 1
    nodes = 0
    for move in generate_legal_moves(board):
        board.make_move(move)
        nodes += perft(board, depth - 1, check_hash)
        board.unmake_move(move)
    return nodes


def divide(board: Board, depth: int) -> None:
    """Print the perft count below each legal move, to locate a wrong subtree."""
    total = 0
    for move in generate_legal_moves(board):
        board.make_move(move)
        nodes = perft(board, depth - 1)
        board.unmake_move(move)
        print(f"{move_to_uci(move)}: {nodes}")
        total += nodes
    print(f"Total: {total}")


def main() -> None:
    check_hash = "--hash" in sys.argv
    all_ok = True
    total_nodes = 0
    start = time.perf_counter()
    for name, fen, depth, expected in POSITIONS:
        position_start = time.perf_counter()
        nodes = perft(Board.from_fen(fen), depth, check_hash)
        seconds = time.perf_counter() - position_start
        ok = nodes == expected
        all_ok = all_ok and ok
        total_nodes += nodes
        status = "OK" if ok else f"FAIL (expected {expected})"
        print(f"{name:<20} depth {depth}  {nodes:>9} nodes  {seconds:6.1f} s  {status}")
    elapsed = time.perf_counter() - start
    print(
        f"Total: {total_nodes} nodes in {elapsed:.1f} s ({total_nodes / elapsed:,.0f} nodes/s)"
    )
    print("All positions OK" if all_ok else "SOME POSITIONS FAILED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
