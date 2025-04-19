
import google.generativeai as genai
import os

genai.configure(api_key='AIzaSyBbWMLwDmRw45HEJm9sgKL6ZHdARUKXE0E')
model = genai.GenerativeModel("gemini-1.5-flash")

def analyze_with_gemini(data):
    prompt = f"""Analyze this expense:
Amount: {data.get('amount')}
Date: {data.get('date')}
Category: {data.get('category')}
Context: {data.get('raw_text')[:300]}...
"""    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini API error: {e}"
