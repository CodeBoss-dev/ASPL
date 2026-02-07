import requests
import time
import sys
import statistics
import json
import urllib.parse

def benchmark(url: str, runs: int = 5):
    api_url = "http://127.0.0.1:8000/parse"
    
    # Check if the user accidentally passed the full API URL instead of just the target URL
    # If they passed "http://127.0.0.1:8000/parse?url=...", we need to extract the actual target URL
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc == "127.0.0.1:8000" and parsed.path == "/parse":
        query = urllib.parse.parse_qs(parsed.query)
        if "url" in query:
            url = query["url"][0]
            print(f"Corrected target URL to: {url}")

    print(f"--- Benchmarking {url} ({runs} runs) ---")
    
    latencies = []
    
    print("\nRunning requests...")
    for i in range(runs):
        start = time.time()
        # Send the target URL as a query parameter
        response = requests.post(api_url, params={"url": url})
        end = time.time()
        
        if response.status_code != 200:
            print(f"Run {i+1}: Error {response.status_code} - {response.text}")
            continue
            
        duration = end - start
        latencies.append(duration)
        print(f"Run {i+1}: {duration:.4f}s")
        
        # Small sleep
        time.sleep(0.5)

    if not latencies:
        return

    print("\n--- Statistics ---")
    print(f"Median: {statistics.median(latencies):.4f}s")
    print(f"Mean:   {statistics.mean(latencies):.4f}s")
    if len(latencies) > 1:
        print(f"Stdev:  {statistics.stdev(latencies):.4f}s")
    
    print("\nNote: Check server logs for detailed stage breakdown (Crawl, Clean, Extract).")

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://www.paulgraham.com/avg.html"
    num_runs = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    benchmark(target_url, num_runs)
