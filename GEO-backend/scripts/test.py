from openai import OpenAI

# 🔑 Replace this with your actual API key
OPENAI_API_KEY = "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"

client = OpenAI(api_key=OPENAI_API_KEY)

prompt = "What are the latest developments in AI regulation in 2026?"

response = client.responses.create(
    model="gpt-5-mini",
    input=prompt,
    tools=[{"type": "web_search"}],
    tool_choice="auto"
)

response_text_parts = []
citations = []

for item in response.output:

    # Assistant message
    if item.type == "message":
        for content_block in item.content:

            if content_block.type == "output_text":
                response_text_parts.append(content_block.text)

                # Extract citations from annotations
                if hasattr(content_block, "annotations") and content_block.annotations:
                    for ann in content_block.annotations:
                        if ann.type == "url_citation":
                            if hasattr(ann, "url") and ann.url:
                                citations.append(ann.url)

    # Tool result (web search results)
    elif item.type == "tool_call_output":
        if hasattr(item, "output") and item.output:
            results = item.output.get("results", [])
            for result in results:
                url = result.get("url")
                if url:
                    citations.append(url)

response_text = "\n".join(response_text_parts).strip()
citations = list(set(citations))

print("\n================ RESPONSE ================\n")
print(response_text)

print("\n================ CITATIONS ================\n")
for i, url in enumerate(citations, 1):
    print(f"{i}. {url}")