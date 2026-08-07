import agent.agent as agent
from langgraph.graph import StateGraph, START, END
import agent.edges as edges

graph= StateGraph(agent.rag_agent)
    
    
#graph
graph= StateGraph(agent.AgentState)
graph.add_node("llm", agent.process)
graph.add_node("tools", agent.take_action)

graph.add_edge(START, "llm")
graph.add_conditional_edges('llm', edges.should_continue,{
    'continue': "tools",
    'end': END  
})
graph.add_edge("tools", "llm")

agent= graph.compile()