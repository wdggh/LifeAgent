"""get_document tool: read a limited context of one Document."""

from app.agent.tools.base import Tool, ToolContext, ToolResult
from app.domain.models.llm import ToolSpec
from app.infrastructure.storage.local_storage import LocalFileStorage
from app.rag.ingestion.errors import ParsingError
from app.rag.ingestion.parser import DocumentParser
from app.repositories.document_repository import DocumentRepository

DEFAULT_MAX_CHARS = 8000
MIN_MAX_CHARS = 200
MAX_MAX_CHARS = 20000


class GetDocumentTool(Tool):
    """Return a limited, page-aware excerpt of one of the user's Documents.

    The full Document is never returned. Access is verified against the
    current user so another user's Document is indistinguishable from a
    missing one.
    """

    name = "get_document"

    def __init__(
        self,
        document_repository: DocumentRepository,
        storage: LocalFileStorage | None = None,
    ) -> None:
        self._documents = document_repository
        self._storage = storage or LocalFileStorage()

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=(
                "Read a limited amount of content from a specific Document "
                "found by search_knowledge, optionally a single page. Use it "
                "to dig deeper into a source before answering. It never "
                "returns the entire document."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"},
                    "page": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Optional 1-based page number",
                    },
                    "max_chars": {
                        "type": "integer",
                        "minimum": MIN_MAX_CHARS,
                        "maximum": MAX_MAX_CHARS,
                    },
                },
                "required": ["document_id"],
            },
        )

    async def run(
        self, arguments: dict, context: ToolContext
    ) -> ToolResult:
        document_id = arguments.get("document_id")
        if not isinstance(document_id, str) or not document_id.strip():
            return ToolResult(text="Error: document_id is required")

        raw_page = arguments.get("page")
        page: int | None = None
        if raw_page is not None:
            try:
                page = int(raw_page)
            except (TypeError, ValueError):
                return ToolResult(text="Error: page must be a positive integer")
            if page < 1:
                return ToolResult(text="Error: page must be a positive integer")

        try:
            max_chars = int(arguments.get("max_chars") or DEFAULT_MAX_CHARS)
        except (TypeError, ValueError):
            return ToolResult(text="Error: max_chars must be an integer")
        max_chars = max(MIN_MAX_CHARS, min(max_chars, MAX_MAX_CHARS))

        document = await self._documents.get_by_id_and_user(
            document_id, context.user_id
        )
        if document is None:
            return ToolResult(
                text="Document not found or not accessible."
            )

        try:
            pages = DocumentParser().parse(
                self._storage.path_for(document.file_path),
                document.file_type,
            )
        except ParsingError as exc:
            return ToolResult(text=f"Could not read the document: {exc.message}")

        selected = []
        if page is not None:
            for parsed in pages:
                if parsed.page == page:
                    selected.append(parsed)
            if not selected:
                return ToolResult(
                    text=f"Page {page} not found in this document."
                )
        else:
            selected = pages

        excerpt = "".join(p.content for p in selected)[:max_chars]
        if page is not None:
            location = f"page {page}"
        else:
            location = "pages " + (
                f"{selected[0].page}-{selected[-1].page}"
                if selected
                else "?"
            )
        return ToolResult(
            text=(
                f"Document content ({document.filename}, {location}, "
                f"truncated to {max_chars} chars):\n{excerpt}"
            )
        )
