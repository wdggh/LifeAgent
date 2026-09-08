# LifeAgent

LifeAgent is a personal information and decision assistant. A user builds a private knowledge base by uploading personal documents; the agent answers natural-language questions by retrieving over that knowledge base and grounding its answer in the sources it found.

## Language

### Identity & ownership

**User**:
A registered person who owns an account and everything stored under it. The backend derives the user's identity from the authenticated session; the client never supplies a user id.
_Avoid_: account holder, client

**Personal knowledge base**:
Everything a user has uploaded and made retrievable. All retrieval and document reads are scoped to the current user; no operation crosses users.
_Avoid_: corpus, vector store

### Content & retrieval

**Document**:
A record of one user-uploaded source file, with a file type and a document type. A document is not the same thing as the chunks it is split into.
_Avoid_: file, attachment

**File type**:
The physical format of a Document: pdf, txt, or markdown in the MVP.
_Avoid_: extension, format

**Document type**:
The semantic category a user assigns to a Document: contract, purchase_record, warranty, manual, note, or other in the MVP.
_Avoid_: category, kind

**Chunk**:
The smallest unit of retrieval and citation: a bounded excerpt of a Document.
_Avoid_: segment, passage

**ChunkMetadata**:
The provenance attached to a Chunk: which user and Document it comes from, the Document type, the page range (`start_page`/`end_page`), the position within the Document, and the embedding model version that produced it. Used for scoping, filtering, and citation.
_Avoid_: metadata (on its own)

**SearchResult**:
One retrieval item produced by the retrieval pipeline: a Chunk together with the scores recorded by the stages that produced it (dense, sparse, fusion, and rerank) and its metadata. SearchResult is internal to retrieval and is never exposed to the frontend; only the Document-level Sources derived from it are surfaced.
_Avoid_: hit, match

**Source**:
The evidence behind a claim in an Answer. The MVP surfaces Sources at Document level to the user; chunk-level detail is kept internally.
_Avoid_: citation (when meaning the Document itself)

### Conversation

**Conversation**:
A user's series of turns with the Agent on one topic.
_Avoid_: session, thread

**Message**:
One turn in a Conversation. A Message is either user or assistant; Agent system prompts are configuration and are never stored as Messages.
_Avoid_: system message

**AgentRun**:
The recorded unit of one answer attempt: the query, status, retrieval count, and duration, kept so an answer can later be replayed and debugged.
_Avoid_: trace

### Agent

**Agent**:
The component that decides whether and how to retrieve the Personal knowledge base for a user's question, and that loops through Tool calls until the question is answerable or the budget is exhausted.
_Avoid_: bot, chatbot

**AgentState**:
The live, internal state of one AgentRun: query, retrieved material, iterations, and status. It is never exposed to the frontend.
_Avoid_: agent context

**Tool**:
A capability the Agent can invoke through the registry. The MVP has two Tools: search_knowledge and get_document.
_Avoid_: function, plugin

**search_knowledge**:
The Tool that searches the current user's Personal knowledge base for relevant Chunks. Every search is implicitly scoped to the current User.
_Avoid_: search, kb_search

**get_document**:
The Tool that reads a limited amount of content from a specific Document, to go deeper on a Source found by search. It never returns an entire Document.
_Avoid_: read_document (when meaning "return the whole file")

### Document lifecycle

**Document status**:
The user-facing state of a Document: uploaded, processing, completed, or failed.
_Avoid_: state

**Processing stage**:
The internal step a Document is currently in: parsing, chunking, embedding, or indexing. Used for diagnosis and logs; the frontend sees only Document status.
_Avoid_: step, phase

### Frontend UI copy

**对话 (Conversation)**:
The Chinese UI label for a Conversation; one 对话 groups a user's turns with the Agent on one topic.
_Avoid_: 会话, 聊天室 (as UI copy for Conversation)

**文档 (Document)**:
The Chinese UI label for a Document; the sidebar entry for the Documents view is 我的文档.
_Avoid_: 文件, 附件, 我的资料 (as UI copy for Document)

**消息 (Message)**:
The Chinese UI label for a Message; a 消息 is either user or assistant.
_Avoid_: 系统消息, 对话内容 (as UI copy for Message)

**来源 (Source)**:
The Chinese UI label for a Source; the Document-level evidence listed under an Answer.
_Avoid_: 引用 (as UI copy for Source, when the Document itself is meant)

**新对话草稿 (New Conversation Draft)**:
The client-side state between clicking 新对话 and the first successful creation of a Conversation: it has no conversation_id and is not a Conversation. The backend Conversation exists only after the first Message is sent.
_Avoid_: 空会话, 未命名会话 (as if a Conversation already existed)
