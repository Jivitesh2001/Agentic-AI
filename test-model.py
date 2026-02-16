from openai import OpenAI

client = OpenAI(
    base_url="http://192.168.30.94:8000/v1",
    api_key="helloworld123",  # matches --api-key
)

response = client.chat.completions.create(
    model="Qwen/Qwen3-14B",
    messages=[{"role": "user", "content": "Hello! How are you? I am going to use this model for Agentic AI tasks. Do you have any suggestions?"}],
)
print(response.choices[0].message.content)