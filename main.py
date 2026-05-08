"""CLI for testing the agent without Telegram.

Usage:
    python main.py "Should I sell my pomegranates today?"
    python main.py "Compare all mandis"
    python main.py "Solapur cha trend kaay?"
"""
import sys
import json
from dotenv import load_dotenv

load_dotenv()

from src.agent import ask_agent


def main():
    if len(sys.argv) < 2:
        query = "Should I sell my pomegranate harvest now or wait? Where is the best price today?"
        print(f"(no query passed, using default: {query!r})\n")
    else:
        query = " ".join(sys.argv[1:])

    result = ask_agent(query)

    print("\n" + "=" * 60)
    print("CONVERSATIONAL ANSWER")
    print("=" * 60)
    print(result["conversational"])

    print("\n" + "=" * 60)
    print("STRUCTURED RECOMMENDATION")
    print("=" * 60)
    print(json.dumps(result["recommendation"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
