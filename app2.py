import os
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

# Load OPENAI_BASE_URL, OPENAI_API_KEY and WEATHER_API_KEY from .env
load_dotenv()

MODEL_NAME = os.getenv("LLM_MODEL", "Qwen/Qwen3.6-35B-A3B-FP8")


def get_base_url() -> str:
    """Return the OpenAI-compatible base URL (<host>/v1).

    The .env value may contain extra path parts (e.g. /v1/access_group or /ui/home/),
    which are not valid API routes, so everything after /v1 is dropped.
    """
    raw = os.environ["OPENAI_BASE_URL"]
    parsed = urlparse(raw)
    return f"{parsed.scheme}://{parsed.netloc}/v1"


# 1. Structured response returned by the agent
class WeatherReport(BaseModel):
    city: str
    temperature_celsius: float
    conditions: str
    humidity: int
    wind_kph: float
    clothing_recommendation: str


# 2. Model served from the internal LLM playground (OpenAI-compatible API)
model = OpenAIChatModel(
    MODEL_NAME,
    provider=OpenAIProvider(
        base_url=get_base_url(),
        api_key=os.environ["OPENAI_API_KEY"],
    ),
)

weather_agent = Agent(
    model=model,
    output_type=WeatherReport,
    # Qwen3 "thinking" output can break structured output, so turn it off.
    model_settings={"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}},
    system_prompt="""
You are a weather assistant.

Always use the weather tool first.

Include:
- city
- temperature
- conditions
- humidity
- wind speed

Provide a clothing recommendation based on the weather.
""",
)


# 3. Tool the LLM can call to fetch live weather
@weather_agent.tool
def get_current_weather(ctx: RunContext[None], city: str) -> dict:
    """Get the current weather for a city using WeatherAPI.

    Args:
        city: Name of the city, e.g. "Kuala Lumpur".
    """
    response = requests.get(
        "https://api.weatherapi.com/v1/current.json",
        params={"key": os.getenv("WEATHER_API_KEY"), "q": city, "aqi": "no"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    return {
        "city": data["location"]["name"],
        "temp": data["current"]["temp_c"],
        "desc": data["current"]["condition"]["text"],
        "humidity": data["current"]["humidity"],
        "wind_kph": data["current"]["wind_kph"],
    }


# 4. Run the agent
if __name__ == "__main__":
    print("🤖 Weather Assistant")
    print("Type 'exit' to quit.\n")

    while True:
        city = input("Enter a city: ").strip()

        if city.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break
        if not city:
            continue

        try:
            result = weather_agent.run_sync(
                f"What is the weather like in {city} right now?"
            )
        except Exception as e:
            print(f"\n⚠️ Could not get weather for '{city}': {e}\n")
            continue

        report: WeatherReport = result.output

        print("\n--- Weather Report ---")
        print(f"🏙️ City: {report.city}")
        print(f"🌡️ Temperature: {report.temperature_celsius}°C")
        print(f"☁️ Conditions: {report.conditions}")
        print(f"💧 Humidity: {report.humidity}%")
        print(f"🌬️ Wind: {report.wind_kph} km/h")
        print(f"🧥 Recommendation: {report.clothing_recommendation}")
        print()
