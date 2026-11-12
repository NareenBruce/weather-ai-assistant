import os
from typing import Literal
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.fallback import FallbackModel
import requests

# Import Agent and RunContext from Pydantic AI
from pydantic_ai import Agent, RunContext

# Load the API keys from your .env file
load_dotenv()


# 1. Define the structured response you want back from the AI
class WeatherReport(BaseModel):
    city: str
    temperature_celsius: float
    conditions: str
    humidity: int
    wind_kph: float
    clothing_recommendation: str


fallback_model = FallbackModel("google:gemini-3.5-flash-lite")
# 2. Initialize the Agent
# We pass the model provider string and set the strict output schema
weather_agent = Agent(
    model=fallback_model,
    output_type=WeatherReport,
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


# 3. Define a local Python function to act as a Tool
# Pydantic AI will read the type hints and the docstring to explain the tool to the LLM
@weather_agent.tool
def get_current_weather(ctx: RunContext[None], city: str) -> dict:
    api_key = os.getenv("WEATHER_API_KEY")

    url = "https://api.weatherapi.com/v1/current.json"

    params = {"key": api_key, "q": city, "aqi": "yes"}

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    return {
        "city": data["location"]["name"],
        "temp": data["current"]["temp_c"],
        "desc": data["current"]["condition"]["text"],
        "humidity": data["current"]["humidity"],
        "wind_kph": data["current"]["wind_kph"],
        "aqi_available": "yes",
    }


# 4. Run the Agent
if __name__ == "__main__":
    print("🤖 Weather Assistant")
    print("Type 'exit' to quit.\n")

    while True:
        city = input("Enter a city: ").strip()

        if city.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break

        result = weather_agent.run_sync(
            f"What is the weather like in {city} right now?"
        )

        report: WeatherReport = result.output

        print("\n--- Weather Report ---")
        print(f"🏙️ City: {report.city}")
        print(f"🌡️ Temperature: {report.temperature_celsius}°C")
        print(f"☁️ Conditions: {report.conditions}")
        print(f"💧 Humidity: {report.humidity}%")
        print(f"🌬️ Wind: {report.wind_kph} km/h")
        print(f"🧥 Recommendation: {report.clothing_recommendation}")
        print()
