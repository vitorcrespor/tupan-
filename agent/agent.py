from re import A
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import agent.agent_tools as agent_tools
from langchain_google_genai import ChatGoogleGenerativeAI
load_dotenv()

class AgentInput(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
tools_list = [agent_tools.get_distance_matrix, agent_tools.check_address,
              agent_tools.latitude_and_longitude, agent_tools.locations_nearby,
              agent_tools.nearest_road,]
tools_dict= {tool.name: tool for tool in tools_list}
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite",
                            temperature=0.3,)
rag_agent= llm.bind_tools(tools_list)
