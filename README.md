🤖 DigitalOcean Gradient™ AI GPU Monitor and Analysis Agent

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
├── main.py               # 🧠 The Orchestrator (LangGraph & Entrypoint)
├── analyzer.py           # 📊 The Engine (Metric processing & threshold logic)
├── metrics.py            # 📡 The Scraper (DO API & DCGM Prometheus parser)
├── config.py             # ⚙️ The Settings (Thresholds & System Prompts)
├── test_local.py         # 🧪 Sandbox: Test AI tool-calling without deployment
└── requirements.txt      # 📦 Python dependency manifest
```

---

## 🔍 Detailed File Breakdown

### ⚙️ `.gradient/agent.yml`
**The Manifest.** This file acts as the "identity card" for your agent. It tells the DigitalOcean Gradient™ platform how to handle your code. It defines the agent’s name, description, and critically, the **entrypoint**—telling the cloud environment exactly which function in `main.py` to execute when a request is received.

### 🔑 `.env`
**The Vault.** A local-only file used to store sensitive credentials like your `DIGITALOCEAN_API_TOKEN` and `GRADIENT_MODEL_ACCESS_KEY`. The code loads these variables at runtime so the agent can talk to your infrastructure securely.

### 🛡️ `.gitignore`
**The Shield.** A vital security configuration that ensures your private secrets stay private. It tells Git to ignore the `.env` file and temporary Python artifacts, preventing accidental leaks of your API keys to public repositories.

### 🧠 `main.py`
**The Orchestrator.** The central nervous system of the agent. It defines the LangGraph state machine, binds the `analyze_gpu_fleet` tool, and manages the conversation flow. It ensures the agent "thinks" before it acts and remembers the context of your conversation using `thread_id`.

### 📊 `analyzer.py`
**The Engine.** Handles the heavy lifting. It filters your fleet for specific slugs (e.g., "gpu") and uses a `ThreadPoolExecutor` to scan multiple nodes in parallel. It categorizes each node as 🔴 Idle, 🟡 Over-provisioned, or 🟢 Optimized.

### 🛡️ `.gitignore`
**The Shield.** A vital security configuration that ensures your private secrets stay private. It tells Git to ignore the `.env` file and temporary Python artifacts, preventing accidental leaks of your API keys to public repositories.

### 📝 `README.md`
**The Blueprint.** The central documentation for the project. It explains the "why" and "how" of the architecture, providing the necessary commands for others to clone, initialize, and deploy the agent.

### 🧠 `main.py`
**The Orchestrator.** This is the core engine of your application, combining three critical AI patterns into a single file to create a functional autonomous agent:
* **The Brain:** It acts as the decision-maker, analyzing user intent to determine when to pull live data or perform local calculations.
* **The Hands:** Implements a robust **MCP (Model Context Protocol) Client**. It handles the complex two-step JSON-RPC "handshake" (Initialize + Call) across 9 distinct DigitalOcean service endpoints using your verified `tool_map` for 100% accuracy.
* **The Memory:** Utilizes LangGraph's **`MemorySaver`** checkpointer. This enables "Session-Aware" intelligence, where the agent stores the entire state of the conversation (including previous tool outputs) under a unique `thread_id` for seamless follow-up questions.

### 📦 `requirements.txt`
**The Ecosystem.** This file manifest ensures the cloud environment is identical to your local setup. It lists the essential libraries,ensuring they are pre-installed in the agent's secure container.
