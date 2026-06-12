from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import agent.agent_tools as agent_tools
from langchain_google_genai import Ch atGoogleGenerativeAI
load_dotenv()

class AgentInput(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
tools_list = [agent_tools.get_pipeline, agent_tools.get_real_state_db, 
              agent_tools.get_analytics, agent_tools.get_client_data]
tools_dict= {tool.name: tool for tool in tools_list}
llm= None
rag_agent= None