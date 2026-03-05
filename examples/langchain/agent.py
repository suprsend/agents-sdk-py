import asyncio
import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain.agents import create_agent

from suprsend_agents_toolkit import SuprSendToolkit, ToolContext

load_dotenv()

toolkit = SuprSendToolkit(
    service_token=os.environ["SUPRSEND_SERVICE_TOKEN"],
    context=ToolContext(workspace=os.environ["SUPRSEND_WORKSPACE"]),
)

agent = create_agent(
    model=ChatAnthropic(model="claude-sonnet-4-6"),
    tools=toolkit.get_langchain_tools(),
)


async def chat() -> None:
    history: list[BaseMessage] = []
    print("SuprSend Agent  (type 'exit' to quit)\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        history.append(HumanMessage(content=user_input))

        result = await agent.ainvoke({"messages": history})
        history = result["messages"]

        final = history[-1]
        if isinstance(final, AIMessage) and final.content:
            print(f"\nAgent: {final.content}\n")


if __name__ == "__main__":
    asyncio.run(chat())