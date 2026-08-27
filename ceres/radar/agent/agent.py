from typing import TypedDict, Annotated, Sequence
import os
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from radar.agent import agent_tools
from langchain_google_genai import ChatGoogleGenerativeAI
load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


# Compatibility name retained for the existing graph contract.
AgentInput = AgentState

# Keep the agent bound only to tools that actually exist in this package.
# These tools delegate to the existing analytics/domain code; they do not
# implement new calculations in the agent layer.
tools_list = [
    agent_tools.price_suggestion,
    agent_tools.negotiation_helper,
    agent_tools.portfolio_analysis,
    agent_tools.property_analysis,
]
tools_dict= {tool.name: tool for tool in tools_list}
llm = ChatGoogleGenerativeAI(model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash-lite"),
                            temperature=0.3,)
rag_agent= llm.bind_tools(tools_list)
