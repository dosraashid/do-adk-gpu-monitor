# 🤖 DigitalOcean Gradient™ AI GPU Monitor and Analysis Agent

This repository demonstrates a production-ready Infrastructure Monitoring Agent built on the DigitalOcean Gradient™ AI Platform. The agent uses LangGraph for stateful reasoning, fetches real-time NVIDIA DCGM metrics from your GPU fleet, and identifies cost-saving opportunities by flagging idle or under-utilized resources.

---

## Architecture Highlights

* **Agent Framework**: LangGraph (`StateGraph`, `ToolNode`)
* **Deployment**: DigitalOcean Gradient™ AI ADK (`@entrypoint`)
* **Inference**: Gradient™ AI Platform using `openai-gpt-oss-120b`
* **Metrics**: Hybrid collection (DO Monitoring API + Direct DCGM Scrapes)
* **Memory**: Thread-isolated session persistence using `MemorySaver()`.

---

## 🏗️ Project Structure & File Guide

A modular architecture designed for the DigitalOcean Gradient™ AI Platform, featuring parallelized metric collection and a stateful reasoning loop.

```text
/do-adk-gpu-monitor
├── .gradient/            # ⚙️ Gradient™ AI Configuration Folder
    └── agent.yml         # 🚀 Deployment Metadata & Routing Config
├── .env                  # 🔑 Local API keys (Never committed to Git)
├── .gitignore            # 🛡️ Security: Prevents sensitive keys from leaking
├── README.md             # 📝 Detailed Project Documentation
├── analyzer.py           # 📊 The Engine (Metric processing & threshold logic)
├── config.py             # ⚙️ The Settings (Thresholds & System Prompts)
├── main.py               # 🧠 The Orchestrator (LangGraph & Entrypoint)
├── metrics.py            # 📡 The Scraper (DO API & DCGM Prometheus parser)
├── requirements.txt      # 📦 Python dependency manifest
└── test_local.py         # 🧪 Sandbox: Test AI tool-calling without deployment
```

---

## 🔍 Detailed File Breakdown

### ⚙️ `.gradient/agent.yml`
**The Manifest.** This file acts as the "identity card" for your agent. It tells the DigitalOcean Gradient™ platform how to handle your code. It defines the agent’s name, description, and critically, the **entrypoint**—telling the cloud environment exactly which function in `main.py` to execute when a request is received.

### 🔑 `.env`
**The Vault.** A local-only file used to store sensitive credentials like your `DIGITALOCEAN_API_TOKEN` and `GRADIENT_MODEL_ACCESS_KEY`. The code loads these variables at runtime so the agent can talk to your infrastructure securely.

### 🛡️ `.gitignore`
**The Shield.** A vital security configuration that ensures your private secrets stay private. It tells Git to ignore the `.env` file and temporary Python artifacts, preventing accidental leaks of your API keys to public repositories.

### 📝 `README.md`
**The Blueprint.** The central documentation for the project. It explains the "why" and "how" of the architecture, providing the necessary commands for others to clone, initialize, and deploy the agent.

### 📊 `analyzer.py`
**The Engine.** Handles the heavy lifting. It filters your fleet for specific slugs (e.g., "gpu") and uses a `ThreadPoolExecutor` to scan multiple nodes in parallel. It categorizes each node as 🔴 Idle, 🟡 Over-provisioned, or 🟢 Optimized.

### ⚙️ `config.py`
**The Settings.** The "Source of Truth" for your agent. Here you define the System Prompt (how the AI speaks) and the Thresholds (what percentage of usage counts as "Idle" vs. "Optimized").

### 🧠 `main.py`
**The Orchestrator.** The central nervous system of the agent. It defines the LangGraph state machine, binds the `analyze_gpu_fleet` tool, and manages the conversation flow. It ensures the agent "thinks" before it acts and remembers the context of your conversation using `thread_id`.

### 📡 `metrics.py`
**The Scraper.** Contains the low-level logic to communicate with the DigitalOcean V2 API. It also includes a custom Prometheus-style parser to scrape NVIDIA DCGM metrics directly from the GPU nodes on port `9400`.

### 📦 `requirements.txt`
**The Ecosystem.** This file manifest ensures the cloud environment is identical to your local setup. It lists the essential libraries,ensuring they are pre-installed in the agent's secure container.

### 🧪 test_local.py
**The Sandbox.** A simplified script to verify your AI can trigger the tools correctly in your local terminal before you commit to a full cloud deployment.

---

# ✨ Key Capabilities

| Capability | Description |
|---|---|
| **GPU Efficiency Analysis** | Deep-dives into NVIDIA DCGM metrics to track Engine Utilization, VRAM usage, and Power Draw. |
| **Parallel Fleet Scanning** | Scans 200+ droplets in seconds using multi-threading to prevent API timeouts. |
| **Cost-Saving Alerts** | Specifically flags high-cost GPU nodes that are currently wasting budget with <2% utilization. |
| **Context-Aware Memory** | Uses `thread_id` to remember previous scans, allowing follow-ups like "Which of those nodes was the most expensive?" |
| **Hybrid Logic Path** | Automatically falls back to standard CPU/RAM monitoring if a node is not a GPU-enabled instance. |

---

# 🚀 Setup & Installation

### 1. Prerequisites
- **Python 3.12** recommended for the latest LangGraph and Asyncio features.
- **DigitalOcean API Token**: Needs `read` permissions for resources and `create`, `read` and `update` scopes on `genai`. [Generate API Token here](https://cloud.digitalocean.com/account/api/tokens).
- **Gradient™ Model Access Key**: Required to access the Serverless Inference endpoint for local testing. [Generate Model Access Key here](https://cloud.digitalocean.com/gen-ai/model-access-keys).

### 2. Environment Setup

Install the required Python dependencies:

```bash
git clone https://github.com/dosraashid/do-adk-gpu-monitor       
cd do-adk-gpu-monitor
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration & Credentials

Update the `.env` file in the root directory. This file is used to authenticate your local session and the cloud-hosted agent.

```bash
# .env

# Used for local testing and to authenticate your session with Serverless Inference engine.
GRADIENT_MODEL_ACCESS_KEY="your_model_access_key"

# Used for agent deployment and to authorize the toolset to audit your DO infrastructure.
# (Requires GenAI Create, Read and Update scopes).
DIGITALOCEAN_API_TOKEN="your_DO_token"
```

Make sure .env is listed in your .gitignore to prevent accidental exposure of secrets.

### 4. Initialization

Before running the agent for the first time, you must initialize the Gradient™ configuration:

```bash
gradient agent init
```

When prompted:

* Agent workspace name: Give it any random name, for example, `Monitor`.
* Agent deployment name: Set this to `main`.

### 5. Export env variables

```
export $(grep -v '^#' .env | xargs)
```

### 6. Test locally

Test the AI logic locally:

```bash
python test_local.py
```

### 7. Run locally

Start the agent server locally using the Gradient™ ADK:

```bash
gradient agent run
```

This will spin up a local Uvicorn server (typically on `http://localhost:8080`). Once it is running, you can issue prompts to the system in a separate terminal tab using `curl`. 

By passing a `thread_id` in your JSON payload, you tell the agent which "save slot" to use, allowing it to maintain conversational memory across multiple requests.

```bash
curl -X POST http://localhost:8080/run \
     -H "Content-Type: application/json" \
     -d '{
           "prompt": "Can you audit my GPU servers?",
           "thread_id": "my-dev-session-1"
         }'
```

### 6. Deployment

Once you have verified the agent's behavior locally, you can deploy it to the DigitalOcean Gradient™ AI Platform cloud. This transforms your local code into a managed, serverless endpoint.

```bash
gradient agent deploy
```

#### Interacting with the Cloud Agent

Once the deployment is successful, you can interact with your agent using a curl command.

```bash
curl -X POST $AGENT_ENDPOINT \
    -H "Authorization: Bearer $DIGITALOCEAN_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "prompt": "Can you audit my GPU servers?",
          "thread_id": "production-audit-1"
        }'
```

Finding your AGENT_ENDPOINT: This URL is printed in your terminal immediately after the deploy command finishes. You can also retrieve it at any time from the DigitalOcean Cloud Panel under the Gradient™ AI Platform page.

**Important: Authorization Token**

The $DIGITALOCEAN_API_TOKEN used in the header must be a Personal Access Token with `read` permissions. [Generate API Token here](https://cloud.digitalocean.com/account/api/tokens). This ensures the request is authorized to trigger the agent's inference engine and execute the underlying MCP tools.

---

## 🧪 Verification Commands & Test Cases

| Test Case | Purpose | Terminal Command (`curl`) | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **1. Status Check** | Verify API Access | `'{"prompt": "Check my fleet status.", "thread_id": "alpha"}'` | Agent runs tool and summarizes nodes. |
| **2. Follow-up** | Test Memory. | `'{"prompt": "Which was the idle one?", "thread_id": "alpha"}'` | Agent remembers the previous list.. |
| **3. Capability** | Test Constraints. | `'{"prompt": "What can you do?", "thread_id": "alpha"}'` | Agent explains monitoring roles without calling tools. |
| **4. Test Thread Isolation** | Prove memory is strictly scoped and isolated. | `'{"prompt": "What was the second question I asked you?", "thread_id": "beta"}'` | Agent looks at the isolated `beta` thread, sees no history, and treats this as a brand-new conversation. |

---

# 🛠️ Troubleshooting

* **Empty Insights `{}`**: Ensure your `.env` is loaded and you have active GPU Droplets. Check the slug filter in `analyzer.py`.
* **Port 8080 Error**: Run `kill -9 $(lsof -ti :8080)` to clear a hanging local server process.
* 0 Nodes Found: Verify the `DIGITALOCEAN_API_TOKEN` has the correct scopes for the account you are auditing.
