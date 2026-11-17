"""Chess position: bitboards, FEN, making and unmaking moves."""

# --- Colors ---
WHITE = 0
BLACK = 1

# --- Piece types ---
PAWN = 0
KNIGHT = 1
BISHOP = 2
ROOK = 3
QUEEN = 4
KING = 5

# --- Pieces: index = color * 6 + piece type ---
PIECE_CHARS = "PNBRQKpnbrqk"
NO_PIECE = 12

# --- Squares: a1 = 0, b1 = 1, ..., h8 = 63 ---
NO_SQUARE = 64
FILE_NAMES = "abcdefgh"
RANK_NAMES = "12345678"

FULL = 0xFFFF_FFFF_FFFF_FFFF

# --- Castling rights: one bit per right ---
WHITE_KINGSIDE = 1
WHITE_QUEENSIDE = 2
BLACK_KINGSIDE = 4
BLACK_QUEENSIDE = 8

# --- FEN ---
CASTLING_CHARS = "KQkq"
STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# --- Move flags (bits 12-15 of a move) ---
QUIET = 0
DOUBLE_PAWN_PUSH = 1
KING_CASTLE = 2
QUEEN_CASTLE = 3
CAPTURE = 4
EN_PASSANT = 5
KNIGHT_PROMOTION = 8
BISHOP_PROMOTION = 9
ROOK_PROMOTION = 10
QUEEN_PROMOTION = 11
KNIGHT_PROMOTION_CAPTURE = 12
BISHOP_PROMOTION_CAPTURE = 13
ROOK_PROMOTION_CAPTURE = 14
QUEEN_PROMOTION_CAPTURE = 15

CAPTURE_BIT = 4
PROMOTION_BIT = 8
NO_MOVE = 0


def square_name(sq: int) -> str:
    """Square index -> name, e.g. 28 -> 'e4'."""
    return FILE_NAMES[sq % 8] + RANK_NAMES[sq // 8]


def parse_square(name: str) -> int:
    """Square name -> index, e.g. 'e4' -> 28."""
    if len(name) != 2:
        raise ValueError(f"Invalid square: {name!r}")
    file = FILE_NAMES.index(name[0])
    rank = RANK_NAMES.index(name[1])
    return rank * 8 + file


def castling_string(castling: int) -> str:
    """Castling rights as in FEN, e.g. 0b1111 -> 'KQkq', 0 -> '-'."""
    result = ""
    for i, char in enumerate(CASTLING_CHARS):
        if castling & (1 << i):
            result += char
    return result or "-"


def encode_move(from_sq: int, to_sq: int, flag: int = QUIET) -> int:
    """Pack a move into one int: from (bits 0-5), to (bits 6-11), flag (bits 12-15)."""
    return from_sq | (to_sq << 6) | (flag << 12)


def move_from(move: int) -> int:
    """Origin square of a move."""
    return move & 0x3F


def move_to(move: int) -> int:
    """Destination square of a move."""
    return (move >> 6) & 0x3F


def move_flag(move: int) -> int:
    """Flag of a move (QUIET, CAPTURE, ...)."""
    return move >> 12


def promotion_type(flag: int) -> int:
    """Piece type a pawn promotes to, for a promotion flag (8-15)."""
    return KNIGHT + (flag & 3)


def move_to_uci(move: int) -> str:
    """Move in UCI notation, e.g. 'e2e4' or 'e7e8q'."""
    if move == NO_MOVE:
        return "0000"
    text = square_name(move_from(move)) + square_name(move_to(move))
    flag = move_flag(move)
    if flag & PROMOTION_BIT:
        text += "nbrq"[flag & 3]
    return text


ALL_CASTLING = (
    WHITE_KINGSIDE | WHITE_QUEENSIDE | BLACK_KINGSIDE | BLACK_QUEENSIDE
)  # == 1 = 0001 | 2 = 0010 | 4 = 0100 | 8 = 1000  ==  1111  =  15


def _build_castling_mask() -> list[int]:
    """For each square: castling rights that survive a move from or to that square."""
    mask = [ALL_CASTLING] * 64
    mask[parse_square("e1")] = ALL_CASTLING ^ (WHITE_KINGSIDE | WHITE_QUEENSIDE)
    mask[parse_square("h1")] = ALL_CASTLING ^ WHITE_KINGSIDE
    mask[parse_square("a1")] = ALL_CASTLING ^ WHITE_QUEENSIDE
    mask[parse_square("e8")] = ALL_CASTLING ^ (BLACK_KINGSIDE | BLACK_QUEENSIDE)
    mask[parse_square("h8")] = ALL_CASTLING ^ BLACK_KINGSIDE
    mask[parse_square("a8")] = ALL_CASTLING ^ BLACK_QUEENSIDE
    return mask


CASTLING_MASK = _build_castling_mask()


class Board:
    """Chess position: piece bitboards, mailbox and game state."""

    __slots__ = (
        "pieces",
        "occupancy",
        "squares",
        "side",
        "castling",
        "ep_square",
        "halfmove_clock",
        "fullmove_number",
        "history",
    )

    def __init__(self) -> None:
        """Create an empty board: no pieces, white to move."""
        self.pieces: list[int] = [0] * 12
        self.occupancy: list[int] = [0, 0]
        self.squares: list[int] = [NO_PIECE] * 64
        self.side: int = WHITE
        self.castling: int = 0
        self.ep_square: int = NO_SQUARE
        self.halfmove_clock: int = 0
        self.fullmove_number: int = 1
        self.history: list[tuple[int, int, int, int]] = []

    def put_piece(self, piece: int, sq: int) -> None:
        """Place a piece on a square. The square must be empty."""
        bit = 1 << sq
        self.pieces[piece] |= bit
        self.occupancy[piece // 6] |= bit
        self.squares[sq] = piece

    def remove_piece(self, sq: int) -> int:
        """Remove the piece from a square and return it. The square must not be empty."""
        piece = self.squares[sq]
        bit = 1 << sq
        self.pieces[piece] ^= bit
        self.occupancy[piece // 6] ^= bit
        self.squares[sq] = NO_PIECE
        return piece

    def make_move(self, move: int) -> None:
        """Play a move. The move is assumed to be legal; it is not checked here."""
        from_sq = move_from(move)
        to_sq = move_to(move)
        flag = move_flag(move)
        us = self.side

        if flag == EN_PASSANT:
            captured_sq = to_sq - 8 if us == WHITE else to_sq + 8
        else:
            captured_sq = to_sq

        captured = self.squares[captured_sq]
        self.history.append(
            (captured, self.castling, self.ep_square, self.halfmove_clock)
        )

        if captured != NO_PIECE:
            self.remove_piece(captured_sq)
        piece = self.remove_piece(from_sq)
        if flag & PROMOTION_BIT:
            self.put_piece(us * 6 + promotion_type(flag), to_sq)
        else:
            self.put_piece(piece, to_sq)

        if flag == KING_CASTLE:
            self.put_piece(self.remove_piece(to_sq + 1), to_sq - 1)
        elif flag == QUEEN_CASTLE:
            self.put_piece(self.remove_piece(to_sq - 2), to_sq + 1)

        self.castling &= CASTLING_MASK[from_sq] & CASTLING_MASK[to_sq]
        if flag == DOUBLE_PAWN_PUSH:
            self.ep_square = (from_sq + to_sq) // 2
        else:
            self.ep_square = NO_SQUARE
        if piece % 6 == PAWN or captured != NO_PIECE:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        if us == BLACK:
            self.fullmove_number += 1
        self.side = us ^ 1

    def unmake_move(self, move: int) -> None:
        """Take back a move played by make_move. Moves must be taken back in reverse order."""
        from_sq = move_from(move)
        to_sq = move_to(move)
        flag = move_flag(move)

        captured, self.castling, self.ep_square, self.halfmove_clock = (
            self.history.pop()
        )
        self.side ^= 1
        us = self.side
        if us == BLACK:
            self.fullmove_number -= 1

        if flag == KING_CASTLE:
            self.put_piece(self.remove_piece(to_sq - 1), to_sq + 1)
        elif flag == QUEEN_CASTLE:
            self.put_piece(self.remove_piece(to_sq + 1), to_sq - 2)

        piece = self.remove_piece(to_sq)
        if flag & PROMOTION_BIT:
            piece = us * 6 + PAWN
        self.put_piece(piece, from_sq)

        if captured != NO_PIECE:
            if flag == EN_PASSANT:
                captured_sq = to_sq - 8 if us == WHITE else to_sq + 8
            else:
                captured_sq = to_sq
            self.put_piece(captured, captured_sq)

    @classmethod
    def from_fen(cls, fen: str) -> "Board":
        """Create a board from a FEN string."""
        fields = fen.split()
        if len(fields) != 6:
            raise ValueError(f"FEN must have 6 fields: {fen!r}")
        placement, side, castling, ep, halfmove, fullmove = fields

        board = cls()
        board._place_pieces_from_fen(placement)

        if side not in ("w", "b"):
            raise ValueError(f"Invalid side to move in FEN: {side!r}")
        board.side = WHITE if side == "w" else BLACK

        if castling != "-":
            for char in castling:
                if char not in CASTLING_CHARS:
                    raise ValueError(f"Invalid castling rights in FEN: {castling!r}")
                board.castling |= 1 << CASTLING_CHARS.index(char)

        board.ep_square = NO_SQUARE if ep == "-" else parse_square(ep)
        board.halfmove_clock = int(halfmove)
        board.fullmove_number = int(fullmove)
        return board

    def _place_pieces_from_fen(self, placement: str) -> None:
        """Place pieces from the first FEN field, e.g. 'rnbqkbnr/pppppppp/8/...'."""
        ranks = placement.split("/")
        if len(ranks) != 8:
            raise ValueError(f"FEN placement must have 8 ranks: {placement!r}")
        for i, rank_text in enumerate(ranks):
            rank = 7 - i
            file = 0
            for char in rank_text:
                if char in "12345678":
                    file += int(char)
                elif char in PIECE_CHARS:
                    if file >= 8:
                        raise ValueError(f"Too many squares in FEN rank: {rank_text!r}")
                    self.put_piece(PIECE_CHARS.index(char), rank * 8 + file)
                    file += 1
                else:
                    raise ValueError(f"Invalid character in FEN placement: {char!r}")
            if file != 8:
                raise ValueError(f"FEN rank must have 8 squares: {rank_text!r}")

    def to_fen(self) -> str:
        """Return the position as a FEN string."""
        side = "w" if self.side == WHITE else "b"
        ep = "-" if self.ep_square == NO_SQUARE else square_name(self.ep_square)
        fields = [
            self._placement_to_fen(),
            side,
            castling_string(self.castling),
            ep,
            str(self.halfmove_clock),
            str(self.fullmove_number),
        ]
        return " ".join(fields)

    def _placement_to_fen(self) -> str:
        """First FEN field: pieces rank by rank, e.g. 'rnbqkbnr/pppppppp/8/...'."""
        rank_texts = []
        for rank in range(7, -1, -1):
            text = ""
            empty = 0
            for file in range(8):
                piece = self.squares[rank * 8 + file]
                if piece == NO_PIECE:
                    empty += 1
                else:
                    if empty > 0:
                        text += str(empty)
                        empty = 0
                    text += PIECE_CHARS[piece]
            if empty > 0:
                text += str(empty)
            rank_texts.append(text)
        return "/".join(rank_texts)

    def __str__(self) -> str:
        """Board diagram followed by the game state."""
        lines = []
        for rank in range(7, -1, -1):
            row = []
            for file in range(8):
                piece = self.squares[rank * 8 + file]
                row.append("." if piece == NO_PIECE else PIECE_CHARS[piece])
            lines.append(RANK_NAMES[rank] + "  " + " ".join(row))
        lines.append("   " + " ".join(FILE_NAMES))

        side = "white" if self.side == WHITE else "black"
        ep = "-" if self.ep_square == NO_SQUARE else square_name(self.ep_square)
        lines.append("")
        lines.append(f"Side to move: {side}")
        lines.append(f"Castling: {castling_string(self.castling)}")
        lines.append(f"En passant: {ep}")
        lines.append(
            f"Halfmove clock: {self.halfmove_clock}, Fullmove: {self.fullmove_number}"
        )
        return "\n".join(lines)
