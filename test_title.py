import os

from google import genai

client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
message = "Halo, saya mau tanya di mana lokasi ruang baca untuk anak-anak ya?"

# Gunakan f-string untuk memasukkan variabel message
prompt = f"""

You are an expert title generator. Create a very short 2-3 word title from this message.

Rules:
- Output ONLY 2-3 words
- NO prefixes, quotes, or explanations
- Use the SAME language as the message
- Extract ONLY the core topic

Message: {message}

Title:"""

response = client.models.generate_content(
    model="gemini-2.5-flash", 
    contents=prompt
)

print(response.text)