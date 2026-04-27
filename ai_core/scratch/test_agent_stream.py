import requests
import json

def test_agent():
    intent = "Analyze the current board and move one existing component slightly to the right by a small offset."
    url = f"http://localhost:8000/api/v1/agent/run?intent={intent}"
    
    print(f"Testing intent: {intent}")
    
    try:
        response = requests.get(url, stream=True, timeout=60)
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: "):
                    data = json.loads(line_str[6:])
                    msg = data.get('message', '').encode('ascii', 'ignore').decode('ascii')
                    print(f"[{data.get('type', 'info')}] {msg}")
                    if data.get('type') == 'tool_selected':
                        print(f"   Tool: {data.get('tool')}")
                    if data.get('type') == 'action':
                        print(f"   Result: {data.get('status')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_agent()
