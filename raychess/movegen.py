"""Move generation: attack tables, attack detection and legal moves."""

from raychess.board import (
    BISHOP,
    BLACK_KINGSIDE,
    BLACK_QUEENSIDE,
    CAPTURE,
    DOUBLE_PAWN_PUSH,
    EN_PASSANT,
    FULL,
    KING,
    KING_CASTLE,
    KNIGHT,
    KNIGHT_PROMOTION,
    KNIGHT_PROMOTION_CAPTURE,
    NO_PIECE,
    NO_SQUARE,
    PAWN,
    QUEEN,
    QUEEN_CASTLE,
    ROOK,
    WHITE,
    WHITE_KINGSIDE,
    WHITE_QUEENSIDE,
    Board,
    encode_move,
    iter_squares,
)

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

# Directions as (file step, rank step). The first four increase the square index
# (north +8, north-east +9, east +1, north-west +7), the last four decrease it.
DIRECTIONS = [(0, 1), (1, 1), (1, 0), (-1, 1), (0, -1), (-1, -1), (-1, 0), (1, -1)]
ROOK_DIRECTIONS = (0, 2, 4, 6)  # N, E, S, W
BISHOP_DIRECTIONS = (1, 3, 5, 7)  # NE, NW, SW, SE


def _ray(sq: int, file_step: int, rank_step: int) -> int:
    """Bitboard of the squares from sq (not included) to the edge of the board in one direction."""
    f, r = sq % 8 + file_step, sq // 8 + rank_step
    ray = 0
    while 0 <= f < 8 and 0 <= r < 8:
        ray |= 1 << (r * 8 + f)
        f += file_step
        r += rank_step
    return ray


# RAYS[direction][sq]: the full ray from sq in that direction, ignoring all pieces.
RAYS = [
    [_ray(sq, file_step, rank_step) for sq in range(64)]
    for file_step, rank_step in DIRECTIONS
]


def _ray_attacks(sq: int, direction: int, occupied: int) -> int:
    """Squares attacked from sq along one ray: up to and including the first piece."""
    ray = RAYS[direction][sq]
    blockers = ray & occupied
    if blockers:
        if (
            direction < 4
        ):  # square index increases: the nearest blocker is the lowest bit
            nearest = (blockers & -blockers).bit_length() - 1
        else:  # square index decreases: the nearest blocker is the highest bit
            nearest = blockers.bit_length() - 1
        ray ^= RAYS[direction][nearest]  # cut off the squares behind the blocker
    return ray


def bishop_attacks(sq: int, occupied: int) -> int:
    """Squares a bishop on sq attacks, given the bitboard of all occupied squares."""
    attacks = 0
    for direction in BISHOP_DIRECTIONS:
        attacks |= _ray_attacks(sq, direction, occupied)
    return attacks


def rook_attacks(sq: int, occupied: int) -> int:
    """Squares a rook on sq attacks, given the bitboard of all occupied squares."""
    attacks = 0
    for direction in ROOK_DIRECTIONS:
        attacks |= _ray_attacks(sq, direction, occupied)
    return attacks


def queen_attacks(sq: int, occupied: int) -> int:
    """Squares a queen on sq attacks: rook and bishop attacks together."""
    return rook_attacks(sq, occupied) | bishop_attacks(sq, occupied)


def is_square_attacked(board: Board, sq: int, by_color: int) -> bool:
    """True if any piece of by_color attacks square sq."""
    pieces = board.pieces
    base = by_color * 6  # index of the attacker's pawn; its other pieces follow
    occupied = board.occupancy[0] | board.occupancy[1]
    # Look from sq: a piece attacks sq exactly when the same piece standing on sq
    # would attack it. Pawns capture only forward, so we use the opposite color's pawn.
    if PAWN_ATTACKS[by_color ^ 1][sq] & pieces[base + PAWN]:
        return True
    if KNIGHT_ATTACKS[sq] & pieces[base + KNIGHT]:
        return True
    if KING_ATTACKS[sq] & pieces[base + KING]:
        return True
    if bishop_attacks(sq, occupied) & (pieces[base + BISHOP] | pieces[base + QUEEN]):
        return True
    if rook_attacks(sq, occupied) & (pieces[base + ROOK] | pieces[base + QUEEN]):
        return True
    return False


def king_square(board: Board, color: int) -> int:
    """Square of the king of the given color. The position must have exactly one."""
    return board.pieces[color * 6 + KING].bit_length() - 1


def in_check(board: Board) -> bool:
    """True if the side to move is in check."""
    us = board.side
    return is_square_attacked(board, king_square(board, us), us ^ 1)


def _piece_attacks(piece_type: int, sq: int, occupied: int) -> int:
    """Attacks of a knight, bishop, rook, queen or king standing on sq."""
    if piece_type == KNIGHT:
        return KNIGHT_ATTACKS[sq]
    if piece_type == BISHOP:
        return bishop_attacks(sq, occupied)
    if piece_type == ROOK:
        return rook_attacks(sq, occupied)
    if piece_type == QUEEN:
        return queen_attacks(sq, occupied)
    return KING_ATTACKS[sq]


def _add_piece_moves(board: Board, moves: list[int]) -> None:
    """Add the moves of knights, bishops, rooks, queens and the king (without castling)."""
    us = board.side
    enemy = board.occupancy[us ^ 1]
    occupied = board.occupancy[us] | enemy
    empty = occupied ^ FULL
    for piece_type in (KNIGHT, BISHOP, ROOK, QUEEN, KING):
        for from_sq in iter_squares(board.pieces[us * 6 + piece_type]):
            attacks = _piece_attacks(piece_type, from_sq, occupied)
            for to_sq in iter_squares(attacks & enemy):
                moves.append(encode_move(from_sq, to_sq, CAPTURE))
            for to_sq in iter_squares(attacks & empty):
                moves.append(encode_move(from_sq, to_sq))


def _add_promotions(
    moves: list[int], from_sq: int, to_sq: int, first_flag: int
) -> None:
    """Add the four promotions of one pawn move: knight, bishop, rook and queen."""
    for flag in range(first_flag, first_flag + 4):
        moves.append(encode_move(from_sq, to_sq, flag))


def _add_pawn_moves(board: Board, moves: list[int]) -> None:
    """Add pawn pushes, double pushes, captures, promotions and en passant captures."""
    us = board.side
    enemy = board.occupancy[us ^ 1]
    squares = board.squares
    forward = 8 if us == WHITE else -8
    start_rank = 1 if us == WHITE else 6  # rank index of the pawns' starting rank
    last_rank = 7 if us == WHITE else 0  # rank index where pawns promote

    for from_sq in iter_squares(board.pieces[us * 6 + PAWN]):
        to_sq = from_sq + forward
        promotes = to_sq // 8 == last_rank

        # Pushes: the square in front must be empty.
        if squares[to_sq] == NO_PIECE:
            if promotes:
                _add_promotions(moves, from_sq, to_sq, KNIGHT_PROMOTION)
            else:
                moves.append(encode_move(from_sq, to_sq))
                # Double push: from the starting rank, both squares in front empty.
                if from_sq // 8 == start_rank and squares[to_sq + forward] == NO_PIECE:
                    moves.append(
                        encode_move(from_sq, to_sq + forward, DOUBLE_PAWN_PUSH)
                    )

        # Captures: diagonally forward, onto an enemy piece.
        attacks = PAWN_ATTACKS[us][from_sq]
        for capture_sq in iter_squares(attacks & enemy):
            if promotes:
                _add_promotions(moves, from_sq, capture_sq, KNIGHT_PROMOTION_CAPTURE)
            else:
                moves.append(encode_move(from_sq, capture_sq, CAPTURE))

        # En passant: diagonally forward, onto the (empty) en passant square.
        if board.ep_square != NO_SQUARE and attacks & (1 << board.ep_square):
            moves.append(encode_move(from_sq, board.ep_square, EN_PASSANT))


def _add_castling_moves(board: Board, moves: list[int]) -> None:
    """Add castling moves.

    Checked here: the castling right, empty squares between king and rook, the king
    not in check and not passing over an attacked square. Whether the king's
    destination is attacked is left to the legality filter, as for any king move.
    """
    us = board.side
    them = us ^ 1
    kingside = WHITE_KINGSIDE if us == WHITE else BLACK_KINGSIDE
    queenside = WHITE_QUEENSIDE if us == WHITE else BLACK_QUEENSIDE
    if not board.castling & (kingside | queenside):
        return  # no castling rights left for this side

    base = 0 if us == WHITE else 56  # first square of the back rank: a1 or a8
    king_sq = base + 4  # e1 or e8
    if is_square_attacked(board, king_sq, them):
        return  # castling out of check is not allowed
    occupied = board.occupancy[0] | board.occupancy[1]

    # Kingside: f and g empty, the king passes over f.
    if board.castling & kingside:
        between = (1 << (base + 5)) | (1 << (base + 6))
        if (occupied & between) == 0 and not is_square_attacked(board, base + 5, them):
            moves.append(encode_move(king_sq, base + 6, KING_CASTLE))

    # Queenside: b, c and d empty, the king passes over d (b may be attacked).
    if board.castling & queenside:
        between = (1 << (base + 1)) | (1 << (base + 2)) | (1 << (base + 3))
        if (occupied & between) == 0 and not is_square_attacked(board, base + 3, them):
            moves.append(encode_move(king_sq, base + 2, QUEEN_CASTLE))


def generate_pseudo_legal_moves(board: Board) -> list[int]:
    """All moves that follow the movement rules; some may leave the own king in check."""
    moves: list[int] = []
    _add_pawn_moves(board, moves)
    _add_piece_moves(board, moves)
    _add_castling_moves(board, moves)
    return moves


def generate_legal_moves(board: Board) -> list[int]:
    """All legal moves: pseudo-legal moves that do not leave the own king in check."""
    us = board.side
    legal = []
    for move in generate_pseudo_legal_moves(board):
        board.make_move(move)
        # After the move it is the opponent's turn; our king must not be attacked.
        if not is_square_attacked(board, king_square(board, us), us ^ 1):
            legal.append(move)
        board.unmake_move(move)
    return legal
