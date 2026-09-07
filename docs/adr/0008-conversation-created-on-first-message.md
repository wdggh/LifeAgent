# A Conversation is created with its first Message; "new chat" is a client-side draft

Status: accepted

The backend lets a Conversation title be null and has no rename/update endpoint, so creating a Conversation when the user clicks 新对话 would leave an unrenamable "新对话" entry in the list even if the user never chats. Frontend V1 instead treats 新对话 as a New Conversation Draft with no `conversation_id`: the first sent Message triggers `POST /conversations` (title = truncated first query), then `POST /chat`, and the conversation list refreshes. Alternatives considered: a title-required creation dialog (rejected: forces naming before thinking) and eager empty Conversations (rejected: dead, unrenamable list entries).
