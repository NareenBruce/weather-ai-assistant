import asyncio
import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

# Load OPENAI_BASE_URL and OPENAI_API_KEY from .env
load_dotenv()

MODEL_NAME = os.getenv("LLM_MODEL", "Qwen/Qwen3.6-35B-A3B-FP8")


def get_base_url() -> str:
    """Return <host>/v1, dropping any extra path (e.g. /models) from the env value."""
    parsed = urlparse(os.environ["OPENAI_BASE_URL"])
    return f"{parsed.scheme}://{parsed.netloc}/v1"


model = OpenAIChatModel(
    MODEL_NAME,
    provider=OpenAIProvider(
        base_url=get_base_url(),
        api_key=os.environ["OPENAI_API_KEY"],
    ),
)

# Plain text agent: no tools, no structured output, just the LLM.
chat_agent = Agent(
    model=model,
    # Turn off Qwen3 "thinking" so replies are direct text.
    model_settings={"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}},
    system_prompt="You are a helpful, friendly assistant. Keep answers clear and concise. You always answer in 1 sentece.",
)


async def main() -> None:
    print(f"💬 Chatbot ({MODEL_NAME})")
    print("Commands: 'exit' to quit, 'reset' to clear memory.\n")

    history = []  # conversation memory, passed back to the agent each turn

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break
        if user_input.lower() == "reset":
            history = []
            print("🧹 Memory cleared.\n")
            continue

        try:
            print("Bot: ", end="", flush=True)
            # Stream the reply token by token
            async with chat_agent.run_stream(user_input, message_history=history) as result:
                async for chunk in result.stream_text(delta=True):
                    print(chunk, end="", flush=True)
            history = result.all_messages()
            print("\n")
        except Exception as e:
            print(f"\n⚠️ Error: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
