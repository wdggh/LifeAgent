# Own page-level parser, LangChain splitter for chunking

Status: accepted

PDF parsing is implemented by our own page-level parser (pypdf/pdfplumber) instead of LangChain Community loaders, so chunks can carry accurate `start_page`/`end_page` and answers can cite "page 3 of the contract". Chunking still uses `RecursiveCharacterTextSplitter` from `langchain-text-splitters`; the splitter algorithm is mature and not worth reimplementing.

Consequences: the Parser emits per-page text; page ranges flow through `ChunkMetadata` and `SearchResult`; MinerU remains a future option for scans and complex layouts.
