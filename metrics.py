import urllib.request
import urllib.error
import json
from config import DIGITALOCEAN_API_TOKEN

# =============================================================================
# 1. CORE API WRAPPER
# =============================================================================
def call_do_api(endpoint):
    """
    A lightweight wrapper for the DigitalOcean V2 API using built-in urllib.
    This avoids external dependencies like 'requests' for faster cloud cold-starts.
    """
    # Build full URL if only the endpoint path was provided
    url = endpoint if endpoint.startswith("http") else f"https://api.digitalocean.com/v2/{endpoint}"
    
    req = urllib.request.Request(url)
    
    # Apply official DigitalOcean authentication headers
    req.add_header("Authorization", f"Bearer {DIGITALOCEAN_API_TOKEN}")
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        # Silently failing here returns an empty dict, which the analyzer handles as 'Unknown'
        print(f"DEBUG: DO API Call failed for {url}: {e}")
        return {}

# =============================================================================
# 2. SYSTEM MONITORING (CPU/RAM/LOAD)
# =============================================================================
def fetch_latest_system_metric(metric_name, host_id, start, end):
    """
    Fetches historical system-level metrics from DigitalOcean's native monitoring service.
    Returns the most recent floating-point value found in the requested time range.
    """
    # Construct the monitoring query for a specific droplet ID
    endpoint = f"monitoring/metrics/droplet/{metric_name}?host_id={host_id}&start={start}&end={end}"
    data = call_do_api(endpoint)
    
    try:
        # DigitalOcean Monitoring returns data in a Prometheus-compatible format:
        # data -> result -> values [[timestamp, value], ...]
        results = data.get("data", {}).get("result", [])
        if results and len(results[0].get("values", [])) > 0:
            # We take the last value in the series (the most recent)
            return float(results[0]["values"][-1][1])
    except Exception:
        pass
    
    return 0.0

# =============================================================================
# 3. GPU MONITORING (NVIDIA DCGM)
# =============================================================================
def fetch_dcgm_metrics(ip_address):
    """
    Scrapes the NVIDIA Data Center GPU Manager (DCGM) exporter.
    DCGM typically exports metrics in a plaintext Prometheus format on port 9400.
    """
    url = f"http://{ip_address}:9400/metrics"
    metrics = {}
    
    try:
        # Strict 2-second timeout is critical here; if a node isn't running DCGM,
        # we don't want to hang the entire fleet analysis loop.
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2) as response:
            # Parse the plaintext response line by line
            lines = response.read().decode('utf-8').splitlines()
            for line in lines:
                # Skip comments and metadata lines
                if line.startswith("#"): continue
                
                parts = line.split()
                if not parts: continue
                
                # The metric value is typically the last element on the line
                val = float(parts[-1])
                
                # Map specific DCGM metric strings to our internal dictionary keys
                if "GPU_TEMP" in line: metrics["gpu_temp"] = val
                elif "POWER_USAGE" in line: metrics["power_usage"] = val
                elif "GPU_UTIL" in line: metrics["gpu_util"] = val
                elif "FB_USED" in line: metrics["vram_used_mb"] = val
                elif "FB_FREE" in line: metrics["vram_free_mb"] = val
    except Exception:
        # If the IP is unreachable or the agent isn't installed, return an empty dict
        pass 
    
    return metrics
