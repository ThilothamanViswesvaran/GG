from openai import OpenAI

# Initialize the client - IMPORTANT: Never hardcode API keys in production!
client = OpenAI(api_key="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")  # Replace with your actual key

try:
    # Create chat completion
    completion = client.chat.completions.create(
        model="gpt-4",  # "gpt-4o-mini" is not a valid model name
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Write a haiku about AI"}
        ]
    )
    
    # Print the response
    print(completion.choices[0].message.content)

except Exception as e:
    print(f"Error: {e}")