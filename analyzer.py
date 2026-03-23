import time
from concurrent.futures import ThreadPoolExecutor
from config import THRESHOLDS
from metrics import call_do_api, fetch_latest_system_metric, fetch_dcgm_metrics

def process_single_droplet(d, start_time, end_time):
    """
    Evaluates the performance and health of a single DigitalOcean Droplet.
    Uses DCGM metrics for GPU nodes and falls back to CPU/RAM for non-GPU or unreachable nodes.
    """
    # --- 1. Extract Basic Metadata ---
    d_id = d.get("id")
    name = d.get("name")
    size_slug = d.get("size_slug", "").lower()
    hourly_price = d.get("size", {}).get("price_hourly", 0.0)
    
    # --- 2. Resolve Networking ---
    # Find the Public IPv4 address required for metrics scraping
    networks = d.get("networks", {}).get("v4", [])
    ip_address = next((n.get("ip_address") for n in networks if n.get("type") == "public"), None)

    # --- 3. Metric Collection ---
    # Attempt to fetch GPU-specific metrics (DCGM). 
    # If this fails (e.g., no agent installed), dcgm_available becomes False.
    dcgm_data = fetch_dcgm_metrics(ip_address) if ip_address else {}
    dcgm_available = bool(dcgm_data)

    # Fetch standard System Metrics (15-min Load and RAM)
    load_15 = round(fetch_latest_system_metric("load_15", d_id, start_time, end_time), 2)
    bytes_to_gb = 1024 ** 3
    m_total = fetch_latest_system_metric("memory_total", d_id, start_time, end_time) / bytes_to_gb
    m_avail = fetch_latest_system_metric("memory_available", d_id, start_time, end_time) / bytes_to_gb
    
    # Calculate RAM utilization percentage
    mem_util = round(((m_total - m_avail) / m_total) * 100, 2) if m_total > 0 else 0.0

    # Default baseline status
    status = "Unknown"
    reason = "Metrics unavailable."
    t_gpu, t_sys = THRESHOLDS["gpu"], THRESHOLDS["system"]

    # --- 4. Logic Path A: GPU Node (DCGM Data exists) ---
    if dcgm_available:
        gpu_util = dcgm_data.get("gpu_util", 0)
        v_used = dcgm_data.get("vram_used_mb", 0)
        v_free = dcgm_data.get("vram_free_mb", 0)
        
        # Calculate VRAM utilization percentage
        v_p = round((v_used / (v_used + v_free) * 100), 2) if (v_used + v_free) > 0 else 0

        # Optimization Threshold Checks
        if gpu_util < t_gpu["idle_util_percent"] and v_p < t_gpu["idle_vram_percent"]:
            status, reason = "Idle", f"GPU Wasted. Engine {gpu_util}%, VRAM {v_p}%."
        elif gpu_util > t_gpu["optimized_util_percent"]:
            status, reason = "Optimized", f"Healthy GPU Load ({gpu_util}%)."
        else:
            status, reason = "Over provisioned", f"GPU under-utilized ({gpu_util}%)."
            
    # --- 5. Logic Path B: System Fallback (Standard Metrics) ---
    else:
        if mem_util < t_sys["idle_ram_percent"] and load_15 < t_sys["idle_load_15"]:
            status, reason = "Idle", f"Proxy: Low Activity. RAM {mem_util}%."
        elif mem_util > t_sys["starved_ram_percent"]:
            status, reason = "Under provisioned", f"Proxy: RAM Starvation ({mem_util}%)."
        else:
            status, reason = "Over provisioned", f"Proxy: Wasted overhead. RAM {mem_util}%."

    return {"name": name, "status": status, "reason": reason, "cost_hr": hourly_price}

def analyze_gpu_droplets():
    """
    Main entry point for infrastructure analysis. 
    Filters for GPU-specific nodes and runs the evaluation in parallel for speed.
    """
    # Define the 5-minute time window for metric lookups
    end_time = int(time.time())
    start_time = end_time - 300 
    
    # Fetch all droplets from the account
    data = call_do_api("droplets?per_page=200")
    all_droplets = data.get("droplets", [])

    # =========================================================================
    # SLUG FILTER: GPU ONLY
    # =========================================================================
    # This ensures we only analyze droplets with "gpu" in their size slug.
    # To monitor all droplets, change this to: target_droplets = all_droplets
    target_droplets = [d for d in all_droplets if "gpu" in d.get("size_slug", "").lower()]
    # =========================================================================

    if not target_droplets:
        return {"summary": "No GPU nodes found.", "insights": {}, "inventory": []}

    inventory = []
    
    # --- 6. Parallel Execution ---
    # Using a ThreadPool to prevent sequential network timeouts from blocking the script.
    # 15 max_workers allows up to 15 nodes to be checked simultaneously.
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(process_single_droplet, d, start_time, end_time) for d in target_droplets]
        for f in futures:
            inventory.append(f.result())

    # --- 7. Aggregation ---
    counts = {"Idle": 0, "Over provisioned": 0, "Optimized": 0, "Under provisioned": 0, "Unknown": 0}
    for item in inventory:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    return {
        "summary": f"Analyzed {len(inventory)} GPU nodes.", 
        "insights": counts, 
        "inventory": inventory
    }
