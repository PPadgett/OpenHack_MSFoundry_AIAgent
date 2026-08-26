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


class AutoApproveMcpRunHandler(RunHandler):
    def __init__(self, mcp_tool: McpTool) -> None:
        self._mcp_tool = mcp_tool

    def submit_mcp_tool_approval(
        self, *, run: ThreadRun, tool_call: RequiredMcpToolCall, **kwargs: Any
    ) -> ToolApproval:
        print(f"[RunHandler] Approving MCP tool call: {tool_call.id} ({tool_call.name})")
        headers = getattr(self._mcp_tool, "headers", None)
        if headers:
            return ToolApproval(tool_call_id=tool_call.id, approve=True, headers=headers)
        return ToolApproval(tool_call_id=tool_call.id, approve=True)


def extract_latest_assistant_text(messages) -> str:
    for msg in messages:
        role = getattr(msg, "role", None)
        if str(role).lower().endswith("assistant"):
            for item in getattr(msg, "content", []):
                if getattr(item, "type", None) == "text":
                    text_obj = getattr(item, "text", None)
                    value = getattr(text_obj, "value", None)
                    if value:
                        return value
    return ""


def main() -> int:
    endpoint = os.getenv("PROJECT_CONNECTION_STRING", DEFAULT_PROJECT_ENDPOINT)
    model_name = os.getenv("FOUNDRY_MODEL_DEPLOYMENT", "gpt-5.4")
    mcp_url = os.getenv("PIZZA_MCP_URL", DEFAULT_MCP_URL)

    mcp_tool = McpTool(
        server_label="contoso_pizza",
        server_url=mcp_url,
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
    mcp_tool.set_approval_mode("never")

    with AgentsClient(endpoint=endpoint, credential=DefaultAzureCredential()) as client:
        toolset = ToolSet()
        toolset.add(mcp_tool)

        agent = client.create_agent(
            model=model_name,
            name="crust-place-order-once",
            instructions=(
                "You are Crust, a pizza ordering assistant. "
                "Use MCP tools for menu, toppings, and orders. "
                "If user provides explicit confirmation, place the order and return order id and summary."
            ),
            toolset=toolset,
            top_p=0.7,
            temperature=0.2,
        )
        print(f"Created agent: {agent.id}")

        thread = client.threads.create()
        print(f"Created thread: {thread.id}")

        prompt = (
            "Place an order now. Details: 1 large pepperoni pizza with extra cheese, pickup, "
            "customer Demo User, phone 555-0100. "
            "Use valid IDs from tool lookups as needed. I explicitly confirm this order. "
            "After placing, return ORDER_ID and final status."
        )

        client.messages.create(thread_id=thread.id, role=MessageRole.USER, content=prompt)

        run1 = client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
        print(f"RUN1 status={getattr(run1, 'status', None)}")
        print(f"RUN1 last_error={getattr(run1, 'last_error', None)}")

        # Force a second turn if the model used tools but did not emit a text answer.
        client.messages.create(
            thread_id=thread.id,
            role=MessageRole.USER,
            content="If the order was placed, reply with ORDER_ID and status only.",
        )
        run2 = client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
        print(f"RUN2 status={getattr(run2, 'status', None)}")
        print(f"RUN2 last_error={getattr(run2, 'last_error', None)}")

        messages = client.messages.list(thread_id=thread.id)
        for msg in messages:
            print(f"DEBUG role={msg.role}")
            for item in getattr(msg, "content", []):
                print(f"DEBUG content_type={getattr(item, 'type', None)}")
        answer = extract_latest_assistant_text(messages)
        print("ASSISTANT_REPLY_START")
        print(answer)
        print("ASSISTANT_REPLY_END")

        client.delete_agent(agent.id)
        print("Deleted agent")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
