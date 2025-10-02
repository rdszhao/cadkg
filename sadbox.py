# %%
from openai import OpenAI

client = OpenAI(
    base_url='http://127.0.0.1:11435/v1',
    api_key='ollama',
)
# %%
query = 'evaluate for physical attack possibilities in regards to the tang plate'
context = make_prompt(query, context_only=True)

response = client.chat.completions.create(
    model='gpt-oss:120b',
    messages=[
        {'role': 'system', 'content': context},
        {'role': 'user', 'content': query}
    ],
	temperature=0.3,
	max_tokens=1000
)
print(response.choices[0].message.content)
# %%
