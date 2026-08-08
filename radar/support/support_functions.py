from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
import schema
from dotenv import load_dotenv
import os
import json 

load_dotenv()
LOG_PATH= os.getenv('LOG_PATH')
TOOL_LOG_PATH= os.getenv('TOOL_LOG_PATH')
SUMMARY_KEEP_MESSAGES= 6
SUMMARY_TRIGGER_MESSAGES= 10

def log(conversation_history: list[BaseMessage]= []):
    """   with open(TOOL_LOG_PATH, "w") as file:
        file.write("tool log\n")
        for message in tool_history:
            file.write(f"Tool: {message.name}\n")
            file.write(f"Tool call id: {message.tool_call_id}\n")
            file.write(f"Result: {message.content}\n\n")
        file.write("log end\n")"""
    
    with open(LOG_PATH, "w", encoding="utf-8") as file:
        for message in conversation_history:
            if isinstance(message, HumanMessage):
                record= {"role": "USER", "content": message.content}
                file.write(json.dumps(record, ensure_ascii=False) + "\n")
            elif isinstance(message, AIMessage) and not message.tool_calls:
                content = content_to_text(message.content)
                if content:
                    record = {"role": "DORCAS", "content": content}
                    file.write(json.dumps(record, ensure_ascii=False) + "\n")
        file.write("log end\n")
            
            
def message_to_text(message) -> str:
    """Convert a LangChain message into compact text for summarization."""
    content= getattr(message, "content", "") or ""
    content= str(content).strip()
    
    if isinstance(message, HumanMessage): role= "USER"
    elif isinstance(message, AIMessage):
        role= "DORCAS"
        if getattr(message, "tool_calls", None):
            tool_names= [tc["name"] for tc in message.tool_calls]
            tool_queries= [tc["query"] for tc in message.tool_calls]
            content= f"Requested tool calls: {tool_names} | {tool_queries}"

    elif isinstance(message, ToolMessage):
        role= f"Tool({message.name})"
        content= content[:1500]
    else:
        role= type(message).__name__

    if not content: return ""
    return f"{role}: {content}"


def update_summary(state: schema.AgentState) -> schema.AgentState:
    """
    Summarize older conversation history into state['summary'].

    This does not generate the final user-facing answer.
    It only updates memory/context.
    """
    messages = list(state["messages"])
    old_summary = state.get("summary", "")

    if len(messages) <= SUMMARY_TRIGGER_MESSAGES:
        return {"summary": old_summary}

    messages_to_summarize = messages[:-SUMMARY_KEEP_MESSAGES]
    transcript_parts = []

    for message in messages_to_summarize:
        text = message_to_text(message)
        if text:
            transcript_parts.append(text)
    transcript = "\n\n".join(transcript_parts)
    if not transcript.strip():
        return {"summary": old_summary}

    system_prompt = SystemMessage(content="""
                            You summarize conversation history for an agent.

                            Create a compact but useful memory summary.

                            Preserve:
                            - user goals and preferences
                            - project architecture decisions
                            - unresolved bugs
                            - important code structure
                            - relevant retrieved document facts
                            - tool results if they matter

                            Do not include irrelevant greetings.
                            Do not invent details.
                            Return only the updated summary.
                            """)

    human_prompt = HumanMessage(content=f"""Previous summary:{old_summary}
                            New conversation section to merge into the summary:
                            {transcript} 
                            Updated summary:
                            """)

    response= schema.lm.invoke([system_prompt,human_prompt])
    return {"summary": response.content.strip()}


def log_ingestion(conversation_history= []) -> list[BaseMessage]:
    with open(LOG_PATH, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            if line.startswith("DORCAS:"):
                content= line.removeprefix("DORCAS:").strip()
                conversation_history.append(AIMessage(content=content))

            elif line.startswith("USER:"):
                content= line.removeprefix("USER:").strip()
                conversation_history.append(HumanMessage(content=content))
        return conversation_history

def content_to_text(content) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "\n".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ).strip()

    return str(content)