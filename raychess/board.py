"""Chess position: bitboards, FEN parsing, board printing."""

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
CASTLING_CHARS = "KQkq"


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
