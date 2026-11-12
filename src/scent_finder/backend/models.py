from pydantic import BaseModel
from .. import __version__


class VersionOut(BaseModel):
    version: str

    @classmethod
    def from_metadata(cls):
        return cls(version=__version__)


class Fragrance(BaseModel):
    id: int | None = None
    name: str
    house: str
    year: int | None = None
    family: str | None = None
    notes: list[str] = []
    accords: list[str] = []
    season: list[str] = []
    price_band: str | None = None
    source: str | None = None
    low_confidence: bool = False
    description: str | None = None
    my_status: str | None = None
    my_rating: int | None = None
    times_worn: int | None = None
    last_worn: str | None = None


class CollectionOut(BaseModel):
    count: int
    items: list[Fragrance]


class ScentDnaOut(BaseModel):
    based_on: str
    profile: dict[str, int]
    you_tend_to_like: list[str]
    family_gaps: list[str]
    favourites: list[str]


class ImportIn(BaseModel):
    text: str
    status: str = "owned"


class ImportMatch(BaseModel):
    input: str
    id: int
    match: str
    already: str | None = None
    score: float


class ImportMiss(BaseModel):
    input: str
    did_you_mean: list[str] = []


class ImportPreviewOut(BaseModel):
    preview: list[ImportMatch]
    unmatched: list[ImportMiss]
    status: str = "owned"


class SaveIn(BaseModel):
    fragrance_ids: list[int]
    status: str = "owned"
    rating: int | None = None


class SaveOut(BaseModel):
    saved: bool
    count: int


class ItemUpdateIn(BaseModel):
    status: str | None = None
    rating: int | None = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatIn(BaseModel):
    messages: list[ChatMessage]


class ToolCall(BaseModel):
    name: str
    args: dict


class MeOut(BaseModel):
    display_name: str | None = None
    shelf_count: int
    by_status: dict[str, int]
    daily_limit: int


class ChatOut(BaseModel):
    remaining_today: int | None = None
    reply: str
    tool_calls: list[ToolCall]
    pending_import: ImportPreviewOut | None = None
    usage: dict[str, int]
