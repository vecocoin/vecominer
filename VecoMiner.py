import json
import requests
import argparse
import time
import multiprocessing
import signal
import threading


# Function to handle command-line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="VECO CLI Miner")

    parser.add_argument("-u", "--username", type=str, default="", help="RPC username (default: none)")
    parser.add_argument("-p", "--password", type=str, default="", help="RPC password (default: none)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="RPC server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=26920, help="RPC server port (default: 26920)")
    parser.add_argument("-a", "--address", type=str, required=True, help="Wallet address to receive mined blocks")
    parser.add_argument("-s", "--ssl", type=int, choices=[0, 1], default=0,
                        help="Use SSL (1 = HTTPS, 0 = HTTP, default: 0)")
    parser.add_argument("-t", "--threads", type=int, default=multiprocessing.cpu_count(),
                        help="Number of mining threads (default: max cores)")
    parser.add_argument("-i", "--iterations", type=int, default=None,  # Default: Auto-calibrate
                        help="Iterations per request (default: auto-adjusted to ~30-second cycles)")

    return parser.parse_args()


# Persistent HTTP session
session = requests.Session()
HEADERS = {"content-type": "application/json"}

# Global stop flag
stop_event = threading.Event()

# Hash rate tracking
thread_hash_rates = {}
hash_rate_lock = threading.Lock()
last_update_time = time.time()  # Ensuring first update at 60s


# RPC Call Function
def rpc_call(method, params, rpc_user, rpc_password, rpc_host, rpc_port, prefix):
    """Sends an RPC request using a persistent connection."""
    payload = json.dumps({"jsonrpc": "2.0", "id": "miner", "method": method, "params": params})
    url = f"{prefix}://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}"

    try:
        response = session.post(url, headers=HEADERS, data=payload, timeout=600)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ RPC Connection Error: {e}")
        return {}


# Auto-Calibration Function
def calibrate_iterations(rpc_user, rpc_password, rpc_host, rpc_port, prefix, coinbase_address, num_threads):
    """Calibrates the optimal number of iterations for ~30-second mining cycles using all available threads."""
    print("🛠  Running calibration with all threads... ")

    # Shared storage for timing results (thread-safe)
    calibration_times = []
    time_lock = threading.Lock()

    # Barrier to synchronize thread start
    start_barrier = threading.Barrier(num_threads)

    def calibrate_single_thread(thread_id):
        """Single thread calibration function."""

        start_barrier.wait()  # Ensure all threads start at the same time

        start_time = time.time()
        rpc_call("generatetoaddress", [1, coinbase_address, 2000], rpc_user, rpc_password, rpc_host, rpc_port, prefix)
        elapsed_time = time.time() - start_time

        # Thread-safe update of timing list
        with time_lock:
            calibration_times.append(elapsed_time)

    # Run calibration on all threads
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=calibrate_single_thread, args=(i,))
        thread.start()
        threads.append(thread)

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    # Compute the **average** time taken across all threads
    if not calibration_times:
        print("⚠️  Calibration failed (no response time measured). Using default 5000 iterations.")
        return 5000

    avg_time_per_thread = sum(calibration_times) / len(calibration_times)

    # Estimate total iterations, considering **all** threads' mining speed
    estimated_iterations = int(2000 * (30 / avg_time_per_thread))  # Scale up for 30s
    adjusted_iterations = max(200, min(estimated_iterations, 20000))  # Ensure sane limits

    print(f"✅ Calibration complete. Adjusting iterations to {adjusted_iterations} for optimal performance.")
    return adjusted_iterations


# Mining Function
def mine_blocks(thread_id, rpc_user, rpc_password, rpc_host, rpc_port, prefix, coinbase_address, iterations):
    """Start a mining thread."""
    print(f"⛏ [Thread {thread_id}] Mining started! Good luck!")

    while not stop_event.is_set():
        start_time = time.time()
        result = rpc_call("generatetoaddress", [1, coinbase_address, iterations], rpc_user, rpc_password, rpc_host,
                          rpc_port, prefix)
        elapsed_time = time.time() - start_time

        if stop_event.is_set():
            break  # Exit if mining is stopped

        # Calculate hash rate
        thread_hash_rate = iterations / elapsed_time if elapsed_time > 0 else 0

        # Store per-thread hash rate
        with hash_rate_lock:
            thread_hash_rates[thread_id] = thread_hash_rate

        if "result" in result and result["result"]:
            print(f"🎉 [Thread {thread_id}] Block found! ✅: {result['result']}")
        else:
            print(f"⛏ [Thread {thread_id}] Mining... Thread Hash Rate: {thread_hash_rate:.2f} H/s")

    print(f"🚪 [Thread {thread_id}] Stopping mining.")


# Separate function to print the total hash rate
def print_total_hash_rate():
    """Handles regular printing of the total hash rate every 30 seconds."""
    global last_update_time

    # Delay first update to 60 seconds
    time.sleep(60)

    while not stop_event.is_set():
        with hash_rate_lock:
            total_hash_rate = sum(thread_hash_rates.values())
            print(f"📊 Total Hash Rate: {total_hash_rate:.2f} H/s")
        last_update_time = time.time()
        time.sleep(30)  # Update every 30 seconds


# Signal Handler for Graceful Shutdown
def signal_handler(sig, frame):
    """Handles Ctrl+C (SIGINT) to stop mining cleanly."""
    print("\n⚠️  Stopping miner... This may take up to 30s.")
    stop_event.set()  # Notify threads to stop


if __name__ == "__main__":
    args = parse_args()

    PREFIX = "https" if args.ssl == 1 else "http"

    print(f"🚀 Starting VECO Miner with {args.threads} threads...")
    print(f"🔗 Connecting to {PREFIX}://{args.host}:{args.port}")
    print(f"💰 Mining rewards sent to: {args.address}")

    # Auto-Calibrate iterations if not provided
    if args.iterations is None:
        args.iterations = calibrate_iterations(args.username, args.password, args.host, args.port, PREFIX, args.address, args.threads)

    print(f"🔄 Iterations per request: {args.iterations}")
    print(f"🔌 Press CTRL+C to stop mining safely.")

    # Register signal handler for CTRL+C
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start hash rate monitor thread
    hash_rate_thread = threading.Thread(target=print_total_hash_rate, daemon=True)
    hash_rate_thread.start()

    # Create mining threads
    threads = []
    for i in range(args.threads):
        thread = threading.Thread(target=mine_blocks, args=(i, args.username, args.password, args.host, args.port, PREFIX,
                                                            args.address, args.iterations), daemon=True)
        thread.start()
        threads.append(thread)

    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        for thread in threads:
            thread.join()
        hash_rate_thread.join()

    print("✅ Miner stopped successfully.")