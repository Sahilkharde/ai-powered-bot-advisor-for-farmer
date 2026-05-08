import os
from typing import Literal
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage

from src.tools import TOOLS
from src.prompts import ADVISOR_SYSTEM_PROMPT, DECISION_INSTRUCTION


class Recommendation(BaseModel):
   
    action: Literal["SELL_NOW", "HOLD", "SELL_PARTIAL", "INSUFFICIENT_DATA"] = Field(
        description="The recommended action."
    )
    recommended_mandi: str = Field(
        description="Best mandi to sell at, or 'N/A' if not selling."
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="How confident the agent is. Be honest — don't default to high."
    )
    reasoning_english: str = Field(
        description="Short reasoning in English (2-3 sentences) referencing the actual numbers seen."
    )
    reasoning_marathi: str = Field(
        description="Same reasoning translated to Marathi for the farmer."
    )
    key_numbers: str = Field(
        description="The actual prices/percentages the recommendation is based on."
    )


def _make_llm(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.environ["GOOGLE_API_KEY"],
        temperature=temperature,
    )


def run_tool_calling_loop(query: str, max_iters: int = 5) -> str:
    
    llm = _make_llm(0.2)
    llm_with_tools = llm.bind_tools(TOOLS)

    tools_by_name = {t.name: t for t in TOOLS}
    messages = [
        SystemMessage(content=ADVISOR_SYSTEM_PROMPT),
        HumanMessage(content=query),
    ]

    response = None
    for i in range(max_iters):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            break  

        print(f"[iter {i}] LLM called {len(tool_calls)} tool(s): "
              f"{[tc['name'] for tc in tool_calls]}")

        for tc in tool_calls:
            tool_fn = tools_by_name.get(tc["name"])
            if tool_fn is None:
                result = f"ERROR: unknown tool '{tc['name']}'"
            else:
                result = tool_fn.invoke(tc["args"])
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    return response.content if response else "No response."


def ask_agent(user_query: str) -> dict:
    """End-to-end: tool loop gathers data, decision LLM emits structured recommendation."""
    
    conversational = run_tool_calling_loop(user_query)

    # Step 2: decision LLM produces structured output, given those findings
    decider = _make_llm(0.1).with_structured_output(Recommendation)
    decision_prompt = (
        f"User asked: {user_query}\n\n"
        f"Findings from the data tools:\n{conversational}\n\n"
        f"{DECISION_INSTRUCTION}"
    )
    rec = decider.invoke([
        SystemMessage(content=ADVISOR_SYSTEM_PROMPT),
        HumanMessage(content=decision_prompt),
    ])

    return {
        "conversational": conversational,
        "recommendation": rec.model_dump(),
    }