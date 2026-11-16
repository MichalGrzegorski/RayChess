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

# --- FEN ---
CASTLING_CHARS = "KQkq"
STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


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
