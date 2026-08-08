import agent.agent as agent
import os
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
import prompts
import support.support_functions as f

CONTEXT_SIZE= int(os.getenv('CONTEXT_SIZE'))
LOG_PATH= os.getenv('LOG_PATH')
DOC_PATH= os.getenv('LOG_PATH_MOD')
TOOL_LOG_PATH= os.getenv('TOOL_LOG_PATH')

async def process(state: agent.AgentState) -> agent.AgentState:
    """processes messages using recent ones."""
    all_messages= list(state["messages"])
    start= max(0, len(all_messages) - CONTEXT_SIZE)

    while start > 0 and not isinstance(all_messages[start], HumanMessage):
        start-= 1
    recent_messages = all_messages[start:]
    
    system_prompt= SystemMessage(content= prompts.SYSTEM_PROMPT)
    response= await agent.rag_agent.ainvoke([system_prompt] + recent_messages)

    print(f"\nLyra: {f.content_to_text(response.content)}")
    return {"messages": [response]}

def should_continue(state: agent.AgentState) -> str: # Returns a string path
    """Check for tool calls on last message"""
    last_message= state['messages'][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return 'continue'
    return 'end'
   
async def take_action(state: agent.AgentState) -> agent.AgentState:
    """The agent takes action based on the tool calls"""
    tool_calls= state['messages'][-1].tool_calls
    results= []
    for tool_call in tool_calls:
        print(f"Processing tool call: {tool_call['name']} with args: {tool_call['args']}")
        
        if not tool_call['name'] in agent.tools_dict:
            print(f"Tool {tool_call['name']} not found.")
            result= "Tool not found."
        else:
            try:
                result = await agent.tools_dict[tool_call['name']].ainvoke(tool_call['args'])
            except Exception as e:
                result = f"Tool error: {type(e).__name__}: {e}"     
                       
            print(f"Tool result: {result}, {len(tool_calls)} steps.")
            results.append(ToolMessage(tool_call_id= tool_call['id'], 
                                       name= tool_call['name'], 
                                       content= result))
            
    print("Completed tool calls.")
    return {'messages': results}

async def running_agent():
    print("\n Bem-vindo")
    if LOG_PATH is None:
        raise ValueError("LOG_PATH is not defined in .env")
    
    conversation_history= f.log_ingestion()
    
    while True:
        user_input= input("USER: ")
        if user_input.lower() == 'exit':
            break
        
        #convo flow
        message= HumanMessage(content= user_input)
        conversation_history.append(message)
        result= await agent.ainvoke({
            "messages": conversation_history})

        conversation_history= result["messages"]
          
        f.log(conversation_history)
    print("Conversation history saved to log.txt")
    


