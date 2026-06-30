import requests

BASE_URL = "http://localhost:8000"

def test_query(topic, document, exact=False):
    print(f"\nTesting Query: topic='{topic}', document='{document}', exact_notes={exact}")
    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={
                "document_name": document,
                "topic": topic,
                "exact_notes": exact
            }
        )
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data.get('response')[:200]}...")
            sentence_count = data.get('response').count('.')
            print(f"Approximate sentences: {sentence_count}")
            return data
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    # Note: Assumes the server is running and has a PDF with "Introduction" or similar topic.
    # This is a manual-triggered test script.
    print("Verification Script")
    # test_query("introduction", "notes", exact=False)
    # test_query("introduction", "notes", exact=True)
