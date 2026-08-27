"""Factory for the existing LangGraph agent workflow.

The graph used to compile at import time through obsolete top-level imports.
Keeping construction behind this factory lets the API initialize it lazily and
return a structured dependency error when its optional LLM dependencies or
credentials are unavailable.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from radar.agent import agent, edges


def build_agent_graph():
    """Compile the existing LLM/tool loop for one reusable API service."""
    workflow = StateGraph(agent.AgentState)
    workflow.add_node("llm", edges.process)
    workflow.add_node("tools", edges.take_action)
    workflow.add_edge(START, "llm")
    workflow.add_conditional_edges("llm", edges.should_continue, {"continue": "tools", "end": END})
    workflow.add_edge("tools", "llm")
    return workflow.compile()
