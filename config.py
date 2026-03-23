import os

# =============================================================================
# 1. AUTHENTICATION & SECRETS
# =============================================================================
# These variables are pulled from your local .env file or Cloud Secrets.
# Note: DIGITALOCEAN_API_TOKEN is the official name required by the Gradient 
# platform to authorize API calls to your infrastructure.
DIGITALOCEAN_API_TOKEN = os.getenv("DIGITALOCEAN_API_TOKEN")
GRADIENT_MODEL_ACCESS_KEY = os.getenv("GRADIENT_MODEL_ACCESS_KEY", "")

# =============================================================================
# 2. AGENT SYSTEM PROMPT (The "Brain")
# =============================================================================
# This prompt defines the persona, behavior, and constraints of the AI.
# It ensures the agent stays on task and doesn't invent data.
AGENT_SYSTEM_PROMPT = """
You are a DigitalOcean Fleet Analyst.

CORE RULES:
1. ONLY use data provided by the 'analyze_gpu_fleet' tool when answering questions about infrastructure.
2. NO HALLUCINATIONS: If the user asks for information not present in the tool output, say you don't know.
3. CONTEXTUAL RESPONSES: 
   - If the user asks "What can you do?", explain that you monitor droplet efficiency. DO NOT run the tool.
   - If the user asks for status, check-up, or to "list" things, run the tool and summarize.
4. If a node is 'Idle', highlight the cost-saving opportunity clearly (mentioning wasted hourly cost).
5. Be concise. Use emojis for status:
   - 🔴 Idle (High priority for shutdown)
   - 🟢 Optimized (Healthy usage)
   - 🟡 Over-provisioned (Consider downsizing)
"""

# =============================================================================
# 3. EVALUATION THRESHOLDS (The "Decision Logic")
# =============================================================================
# These values are used by analyzer.py to categorize droplets based on metrics.
# You can tune these to match your specific production requirements.
THRESHOLDS = {
    "gpu": {
        # Critical Alert Thresholds
        "max_temp_c": 82.0,
        "max_util_percent": 95.0,
        "max_vram_percent": 95.0,
        
        # Idle Definition: Low compute and low VRAM usage
        "idle_util_percent": 2.0,
        "idle_vram_percent": 5.0,
        
        # Optimization Targets: Aiming for at least 40% engine utilization
        "optimized_util_percent": 40.0,
        "optimized_vram_percent": 50.0,
    },
    "system": {
        # Fallback logic for CPU/RAM only nodes or nodes missing GPU metrics
        "idle_cpu_percent": 3.0,
        "idle_ram_percent": 15.0,
        "idle_load_15": 0.5,
        
        # Resource Starvation: Indicates a need to scale up (Under-provisioned)
        "starved_cpu_percent": 85.0,
        "starved_ram_percent": 90.0,
        
        # Healthy CPU/RAM Baseline
        "optimized_cpu_percent": 40.0,
        "optimized_ram_percent": 50.0,
    }
}
