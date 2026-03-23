import json
import os
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from gradient_adk import entrypoint, RequestContext

# Internal project imports
from analyzer import analyze_gpu_droplets
from config import AGENT_SYSTEM_PROMPT, GRADIENT_MODEL_ACCESS_KEY
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import tool

# =============================================================================
# 1. AGENT STATE DEFINITION
# =============================================================================
class AgentState(TypedDict):
    """
    The 'State' keeps track of the conversation history.
    The Annotated list with a lambda function ensures that new messages are 
    appended (x + y) to the history rather than overwriting it.
    """
    messages: Annotated[list[BaseMessage], lambda x, y: x + y]

# =============================================================================
# 2. LLM & TOOL SETUP
# =============================================================================

# Initialize the Chat Model using DigitalOcean's serverless inference endpoint
llm = ChatOpenAI(
    base_url="https://inference.do-ai.run/v1",
    api_key=GRADIENT_MODEL_ACCESS_KEY,
    model="openai-gpt-oss-120b"
)

@tool
def analyze_gpu_fleet():
    """
    Fetches real-time efficiency metrics for DigitalOcean nodes.
    Use this only when the user asks for status, health, or costs.
    """
    # This calls the logic in analyzer.py which scans your droplets
    return json.dumps(analyze_gpu_droplets())

# Bind tools to the LLM so it understands it has the "analyze_gpu_fleet" capability
tools = [analyze_gpu_fleet]
llm_with_tools = llm.bind_tools(tools)

# =============================================================================
# 3. GRAPH NODES & ROUTING LOGIC
# =============================================================================

def call_model(state: AgentState):
    """
    The 'Agent' node. Processes the current message list and decides 
    if it needs to use a tool or just respond.
    """
    messages = state['messages']
    
    # Injected Persona: Ensure the System Prompt is present in new threads
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + messages
        
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def should_continue(state: AgentState):
    """
    The 'Router'. Checks the last AI message to see if a tool call was requested.
    """
    last_message = state['messages'][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# --- Define the Workflow Graph ---
workflow = StateGraph(AgentState)

# Add functional nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))

# Set entry point and routing edges
workflow.add_edge(START, "agent")

# Logic: After 'agent', either go to 'tools' or 'END' the conversation
workflow.add_conditional_edges(
    "agent", 
    should_continue, 
    {"tools": "tools", END: END}
)

# After tools are executed, always return to the agent to summarize the data
workflow.add_edge("tools", "agent")

# Initialize Checkpoint Memory (stores conversation history in RAM)
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

# =============================================================================
# 4. CLOUD ENTRYPOINT (DigitalOcean ADK)
# =============================================================================

@entrypoint
async def main(input: dict, context: RequestContext):
    """
    The main handler for incoming requests from the cloud.
    """
    prompt = input.get("prompt", "")
    
    # Identify the unique thread to pull history from memory
    thread_id = input.get("thread_id", "default-session")
    config = {"configurable": {"thread_id": thread_id}}

    # Execute the graph
    inputs = {"messages": [HumanMessage(content=prompt)]}
    final_state = await app.ainvoke(inputs, config)
    
    # Extract the AI's final natural language response
    final_response = final_state["messages"][-1].content

    # --- OPTIONAL CONTEXT DATA LOGIC ---
    # To return raw JSON data to the client, uncomment the blocks below.
    
    # detail_keywords = ["list", "detail", "inventory", "table", "which", "show me"]
    # is_detailed = any(word in prompt.lower() for word in detail_keywords)
    # inventory_data = []
    # if is_detailed:
    #     # Fetch raw data for the response payload if requested
    #     inventory_data = analyze_gpu_droplets()["inventory"]

    return {
        "response": final_response,
        # "context_data": inventory_data if is_detailed else []  # Uncomment to enable raw data return
    }
