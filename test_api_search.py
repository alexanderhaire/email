import requests
import json

base_url = "http://localhost:5000/api/search"

def test_search(mode, q):
    print(f"Testing mode: {mode}, query: {q}")
    try:
        response = requests.get(base_url, params={"mode": mode, "q": q})
        print(f"Status: {response.status_code}")
        print(f"Results: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Note: This assumes the server is running on localhost:5000
    test_search("invoices", "ya")
    print("-" * 20)
    test_search("purchasing", "ya")
