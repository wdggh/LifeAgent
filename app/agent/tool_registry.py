"""Registry mapping tool names to implementations."""

from app.agent.tools.base import Tool, ToolContext, ToolResult
from app.domain.models.llm import ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.spec.name] = tool

    def specs(self) -> list[ToolSpec]:
        return [tool.spec for tool in self._tools.values()]

    async def execute(
        self, name: str, arguments: dict, context: ToolContext
    ) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(
                text=f"Error: unknown tool '{name}'",
                error=f"unknown tool '{name}'",
            )
        return await tool.run(arguments, context)
