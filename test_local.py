import json
from analyzer import analyze_gpu_droplets
from config import GRADIENT_MODEL_ACCESS_KEY, DIGITALOCEAN_API_TOKEN
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

# This block ensures the code only runs when you execute this file directly
if __name__ == "__main__":
    print("--- Starting Local AI Test ---")
    
    # 1. CREDENTIAL CHECK
    # Validates that your .env file was loaded correctly before making an expensive API call
    if not DIGITALOCEAN_API_TOKEN or not GRADIENT_MODEL_ACCESS_KEY:
        print("WARNING: Missing DIGITALOCEAN_API_TOKEN or GRADIENT_MODEL_ACCESS_KEY.")

    # 2. TOOL DEFINITION
    # The docstring inside the tool is what the AI reads to understand 
    # when it should use this specific function.
    @tool
    def gpu_monitor_tool():
        """Use this tool to check GPU droplet efficiency on DigitalOcean."""
        return json.dumps(analyze_gpu_droplets())

    # 3. LLM INITIALIZATION
    # We use DigitalOcean's serverless inference endpoint.
    # .bind_tools() gives the LLM the "blueprint" of our gpu_monitor_tool.
    llm = ChatOpenAI(
        base_url="https://inference.do-ai.run/v1",
        api_key=GRADIENT_MODEL_ACCESS_KEY,
        model="openai-gpt-oss-120b"
    ).bind_tools([gpu_monitor_tool])

    # 4. THE TEST QUERY
    # We use a prompt that specifically triggers a need for data.
    query = "Check my DigitalOcean account. Do I have any idle GPUs?"
    print(f"User: {query}")
    
    # Send the query to the LLM
    response = llm.invoke([HumanMessage(content=query)])
    
    # 5. RESPONSE HANDLING
    # The LLM doesn't actually 'run' the tool; it returns a 'tool_call' request 
    # asking US (the code) to run it for them.
    if response.tool_calls:
        print(f"\n[AI decided to call tool: {response.tool_calls[0]['name']}]\n")
        
        # Manually execute the analysis logic to verify the data pipe is open
        result = analyze_gpu_droplets()
        
        print("Tool Output Summary:")
        # We print just the 'insights' (the counts) for a clean console view
        print(json.dumps(result["insights"], indent=2))
        
        print("\n(Note: In the full main.py workflow, this JSON is passed back to the LLM to generate a human-friendly response).")
    else:
        # This occurs if the AI thinks it can answer without the tool
        print(f"AI Response: {response.content}")
