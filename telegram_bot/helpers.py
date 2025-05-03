import requests

def get_agent_response(query):
    url = "http://0.0.0.0:8000/chat"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {
        "message": query
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}