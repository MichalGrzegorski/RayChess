"""Move generation: attack tables, attack detection and legal moves."""

# (file, rank) steps of the pieces whose moves do not depend on other pieces.
KNIGHT_OFFSETS = [
    (1, 2),
    (2, 1),
    (2, -1),
    (1, -2),
    (-1, -2),
    (-2, -1),
    (-2, 1),
    (-1, 2),
]
KING_OFFSETS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def _leaper_attacks(sq: int, offsets: list[tuple[int, int]]) -> int:
    """Bitboard of the squares reached from sq by the given steps, staying on the board."""
    file, rank = sq % 8, sq // 8
    attacks = 0
    for file_step, rank_step in offsets:
        f, r = file + file_step, rank + rank_step
        if 0 <= f < 8 and 0 <= r < 8:
            attacks |= 1 << (r * 8 + f)
    return attacks


KNIGHT_ATTACKS = [_leaper_attacks(sq, KNIGHT_OFFSETS) for sq in range(64)]
KING_ATTACKS = [_leaper_attacks(sq, KING_OFFSETS) for sq in range(64)]
# PAWN_ATTACKS[color][sq]: the two squares diagonally in front of a pawn of that color.
PAWN_ATTACKS = [
    [_leaper_attacks(sq, [(-1, 1), (1, 1)]) for sq in range(64)],  # WHITE = 0: rank + 1
    [
        _leaper_attacks(sq, [(-1, -1), (1, -1)]) for sq in range(64)
    ],  # BLACK = 1: rank - 1
]
