import os
from typing import Any

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole
from azure.ai.agents.models import McpTool, ToolApproval, ThreadRun, RequiredMcpToolCall, RunHandler, ToolSet


load_dotenv(override=True)


DEFAULT_PROJECT_ENDPOINT = "https://my-ai-service-2364654.services.ai.azure.com/api/projects/proj-2364654"
DEFAULT_MCP_URL = "https://ca-pizza-mcp-ceki46omdafoe.gentlehill-7ae690c8.westus3.azurecontainerapps.io/sse"


def build_project_client() -> AgentsClient:
    endpoint = os.getenv("PROJECT_CONNECTION_STRING", DEFAULT_PROJECT_ENDPOINT)
    return AgentsClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )


def build_mcp_tool() -> McpTool:
    server_url = os.getenv("PIZZA_MCP_URL", DEFAULT_MCP_URL)

    mcp_tool = McpTool(
        server_label="contoso_pizza",
        server_url=server_url,
        allowed_tools=[
            "get_pizzas",
            "get_pizza_by_id",
            "get_toppings",
            "get_topping_by_id",
            "get_topping_categories",
            "get_orders",
            "get_order_by_id",
            "place_order",
            "delete_order_by_id",
        ],
    )
    # Keep explicit run_handler approvals enabled; forcing "never" can create
    # inconsistent behavior across SDK/runtime combinations.
    return mcp_tool


class AutoApproveMcpRunHandler(RunHandler):
    def __init__(self, mcp_tool: McpTool) -> None:
        self._mcp_tool = mcp_tool

    def submit_mcp_tool_approval(
        self, *, run: ThreadRun, tool_call: RequiredMcpToolCall, **kwargs: Any
    ) -> ToolApproval:
        print(f"[RunHandler] Approving MCP tool call: {tool_call.id} ({tool_call.name})")
        headers = getattr(self._mcp_tool, "headers", None)
        if headers:
            return ToolApproval(
                tool_call_id=tool_call.id,
                approve=True,
                headers=headers,
            )
        return ToolApproval(tool_call_id=tool_call.id, approve=True)


def extract_latest_text(messages) -> str:
    message_list = list(messages)
    for message in reversed(message_list):
        role = str(getattr(message, "role", "")).lower()
        if "assistant" not in role and "agent" not in role:
            continue
        for item in message.content:
            item_type = getattr(item, "type", None)
            if item_type in {"text", "output_text"}:
                text_obj = getattr(item, "text", None)
                value = getattr(text_obj, "value", None)
                if value:
                    return value
                value = getattr(item, "value", None)
                if value:
                    return value
    return ""


def main() -> int:
    model_name = os.getenv("FOUNDRY_MODEL_DEPLOYMENT", "gpt-5.4")
    default_user_id = os.getenv("CONTOSO_PIZZA_USER_ID", "").strip()

    with build_project_client() as project_client:
        mcp_tool = build_mcp_tool()
        toolset = ToolSet()
        toolset.add(mcp_tool)

        agent = project_client.create_agent(
            model=model_name,
            name="crust-live-chat",
            instructions=(
                "You are Crust, a pizza ordering assistant with a friendly persona. "
                "Use MCP tools for menu, toppings, pricing, and orders on every relevant turn. "
                "Do not repeat stale menu text; answer the current user question directly. "
                "Always confirm order details before placing an order. "
                f"For place_order calls, use lab userId '{default_user_id}' unless the user provides another valid userId."
            ),
            toolset=toolset,
            top_p=0.7,
            temperature=0.7,
        )
        print(f"Created agent: {agent.id}")

        thread = project_client.threads.create()
        print(f"Created thread: {thread.id}")

        run_handler = AutoApproveMcpRunHandler(mcp_tool)

        try:
            while True:
                user_input = input("You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit"]:
                    break

                project_client.messages.create(
                    thread_id=thread.id,
                    role=MessageRole.USER,
                    content=user_input,
                )

                run = project_client.runs.create_and_process(
                    thread_id=thread.id,
                    agent_id=agent.id,
                    run_handler=run_handler,
                )

                run_status = str(getattr(run, "status", ""))
                if "failed" in run_status.lower() or "cancelled" in run_status.lower():
                    print(f"Crust: [Run status: {run_status}]")
                    print(f"Crust: [Run error: {getattr(run, 'last_error', None)}]")

                messages = project_client.messages.list(thread_id=thread.id)
                answer = extract_latest_text(messages)
                print(f"Crust: {answer or '[No text response returned by agent]'}")
        finally:
            project_client.delete_agent(agent.id)
            print("Deleted agent")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
