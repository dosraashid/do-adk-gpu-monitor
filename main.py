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
# 1. AGENT STATE MANAGEMENT
# =============================================================================
class AgentState(TypedDict):
    """
    Defines the 'schema' for our agent's memory.
    The Annotated list with the lambda reducer ensures that every time a node 
    returns a message, it is APPENDED to the history rather than replacing it.
    """
    messages: Annotated[list[BaseMessage], lambda x, y: x + y]

# =============================================================================
# 2. LLM & TOOL DEFINITION
# =============================================================================

# Initialize the Chat Model using DigitalOcean's serverless inference
llm = ChatOpenAI(
    base_url="https://inference.do-ai.run/v1",
    api_key=GRADIENT_MODEL_ACCESS_KEY,
    model="openai-gpt-oss-120b"
)

@tool
def analyze_gpu_fleet():
    """
    Fetches real-time efficiency metrics for DigitalOcean nodes.
    Use this tool ONLY when the user asks for status, health checks, 
    inventory, or costs.
    """
    # This calls the fast, parallelized logic in analyzer.py
    return json.dumps(analyze_gpu_droplets())

# Bind the tools to the LLM so it knows it can 'call' them if needed
tools = [analyze_gpu_fleet]
llm_with_tools = llm.bind_tools(tools)

# =============================================================================
# 3. GRAPH NODE LOGIC
# =============================================================================

def call_model(state: AgentState):
    """
    The 'Brain' node. Processes the message history and decides the next move.
    """
    messages = state['messages']
    
    # Inject the System Prompt if this is a brand new conversation
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + messages
        
    response = llm_with_tools.invoke(messages)
    
    # Return the AI's response to be added to the state
    return {"messages": [response]}

def should_continue(state: AgentState):
    """
    The 'Router'. Checks if the AI wants to use a tool or just talk.
    """
    last_message = state['messages'][-1]
    
    # If the LLM generated 'tool_calls', go to the 'tools' node
    if last_message.tool_calls:
        return "tools"
    
    # Otherwise, stop and return the final answer to the user
    return END

# =============================================================================
# 4. GRAPH CONSTRUCTION
# =============================================================================

# Initialize the state machine
workflow = StateGraph(AgentState)

# Define our two functional nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))

# Set the entry point
workflow.add_edge(START, "agent")

# Add conditional logic: Agent -> Tools OR Agent -> End
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", END: END}
)

# After tools are executed, always loop back to the agent for a final summary
workflow.add_edge("tools", "agent")

# Enable memory checkpointing (RAM-based for local/session persistence)
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

# =============================================================================
# 5. CLOUD ENTRYPOINT
# =============================================================================

@entrypoint
async def main(input: dict, context: RequestContext):
    """
    The primary handler for requests from the DigitalOcean Gradient Platform.
    """
    prompt = input.get("prompt", "")
    
    # Retrieve the thread_id to ensure context is maintained across multiple curls
    thread_id = input.get("thread_id", "default-session")
    config = {"configurable": {"thread_id": thread_id}}

    # Invoke the LangGraph workflow
    inputs = {"messages": [HumanMessage(content=prompt)]}
    final_state = await app.ainvoke(inputs, config)
    
    # Extract the AI's final natural language response
    final_response = final_state["messages"][-1].content

    # --- OPTIONAL: CONTEXT DATA (RAW JSON PAYLOAD) ---
    # Uncomment the block below if you eventually need to return the full JSON 
    # inventory in the response payload for a frontend dashboard/table.
    
    # detail_keywords = ["list", "detail", "inventory", "table", "which", "show me"]
    # is_detailed = any(word in prompt.lower() for word in detail_keywords)
    # inventory_data = []
    # if is_detailed:
    #     inventory_data = analyze_gpu_droplets()["inventory"]

    return {
        "response": final_response,
        # "context_data": inventory_data if is_detailed else [] # Uncomment to enable raw data return
    }
