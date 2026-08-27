from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from dotenv import load_dotenv
import os
import json 
from radar.agent import agent
import concurrent.futures
from typing import Dict, List, Optional
import googlemaps
from pydantic import BaseModel
import radar.data_base.data_type as data

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


def update_summary(state: agent.AgentState) -> agent.AgentState:
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

    response= agent.llm.invoke([system_prompt,human_prompt])
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

import numpy as np


def calculate_shannon_entropy(probabilities: np.ndarray) -> float:
    p= probabilities[probabilities > 0]
    if len(p) <= 1:
        return 0.0
    entropy= -np.sum(p * np.log(p))
    max_entropy= np.log(len(probabilities)) 
    return float(entropy/max_entropy) if max_entropy> 0 else 0.0


POI_IMPACT_WEIGHTS: Dict[str, float] = {
    "subway_station": 10.0,
    "transit_station": 8.0,
    "supermarket": 6.0,
    "park": 5.0,
    "school": 5.0,
    "shopping_mall": 4.0,
    "restaurant": 2.0,
    "bar": -2.0,
    "night_club": -4.0,
    "waste_management": -10.0,
}


async def fetch_google_neighbors(latitude: float, longitude: float, gmaps_client: googlemaps.Client,
                        radius_meters: int = 500,) -> List[data.map_point]:
    try:
        response= gmaps_client.places_nearby(
        location=(latitude, longitude), radius=radius_meters)
    except Exception as e:
        print(f"Error fetching Google Places for ({latitude}, {longitude}): {e}")
        return []

    neighbors: List[data.map_point]= []

    for place in response.get("results", []):
        loc= place.get("geometry", {}).get("location", {})
        lat= loc.get("lat")
        lng= loc.get("lng")

        if lat is None or lng is None:
            continue

        types= place.get("types", [])
        rating= place.get("rating", 3.0) 

        type_impact= sum(POI_IMPACT_WEIGHTS.get(t, 0.5) for t in types)

        rating_multiplier= rating/5.0
        calculated_impact= type_impact*rating_multiplier

        neighbors.append(data.map_point(
                latitude=lat,
                longitude=lng,
                impact_score=calculated_impact,
            ))

    return neighbors


import googlemaps


def populate_real_estate_neighbors_gmaps(
    real_estates,
    api_key: str,
    max_distance_meters: int = 2000,
    max_duration_seconds: int = 600,
    mode: str = "driving",
):
    """Populates `.neighbors` for each real_estate object using Google Maps

    Distance Matrix API based on actual driving/walking distance or time.
    """
    gmaps = googlemaps.Client(key=api_key)

    # Extract coordinates or addresses for each property
    def get_location(re):
        lat = getattr(re, "latitude", None)
        lng = getattr(re, "longitude", None)
        if lat is not None and lng is not None:
            return (lat, lng)
        return getattr(re, "address", None)

    locations = [get_location(re) for re in real_estates]

    # Initialize neighbors list for all properties
    for re in real_estates:
        re.neighbors = []

    n = len(real_estates)
    batch_size = 10  # Google Maps Distance Matrix supports up to 25 origins/destinations per request

    # Process in batches to respect API limits
    for i in range(0, n, batch_size):
        origins = locations[i : i + batch_size]
        origin_objs = real_estates[i : i + batch_size]

        for j in range(0, n, batch_size):
            destinations = locations[j : j + batch_size]
            dest_objs = real_estates[j : j + batch_size]

            # Query Google Maps Distance Matrix API
            response = gmaps.distance_matrix(
                origins=origins, destinations=destinations, mode=mode
            )

            for row_idx, row in enumerate(response["rows"]):
                origin_re = origin_objs[row_idx]

                for col_idx, element in enumerate(row["elements"]):
                    dest_re = dest_objs[col_idx]

                    # Skip self-comparison
                    if origin_re is dest_re:
                        continue

                    if element.get("status") == "OK":
                        dist_val = element["distance"]["value"]  # in meters
                        dur_val = element["duration"]["value"]  # in seconds

                        if (
                            dist_val <= max_distance_meters
                            and dur_val <= max_duration_seconds
                        ):
                            origin_re.neighbors.append(dest_re)

    return real_estates
