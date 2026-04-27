import google.generativeai as genai

api_key = "AIzaSyBuRNmuWjCpbQvZ5B-LIJl4cMu5YnVxQU8"
genai.configure(api_key=api_key)

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"ERROR: {e}")
