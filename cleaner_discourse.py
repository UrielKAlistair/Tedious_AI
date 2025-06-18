from pathlib import Path
import httpx
import base64
import requests
import time 
import json
import os

from bs4 import BeautifulSoup

from google import genai
import openai

BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
MAX_RETRIES = 5
DESCRIBE_IMAGE_PROMPT = """
You are an AI system preparing semantic embeddings for a retrieval-augmented generation (RAG) pipeline focused on software engineering discussions.

The input is an image from a technical forum. Describe it with maximum semantic detail, as if you were helping an AI system understand and retrieve it in response to future queries.

Focus on:

Visible code, configuration, console output, error messages, file names, or UI elements

Text in the image (e.g., logs, filenames, YAML keys, JSON, HTML, function names, test cases)

Programming context (e.g., “Python test suite”, “Postman API request”, “VSCode interface with Python script”)

Purpose or activity (e.g., “debugging test failure”, “YAML config showing OpenAI API keys”, “Flask app terminal output”)

Any specific technologies, file types, tools, or platforms visible (e.g., Flask, Jupyter, VSCode, GitHub, pytest, etc.)

Avoid generic phrases like "this is an image of..."; just describe the content directly and concisely in one dense paragraph.
"""
class RateLimiter:
    def __init__(self, requests_per_minute=60, requests_per_second=2):
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_second
        self.request_times = []
        self.last_request_time = 0
    
    def wait_if_needed(self):
        current_time = time.time()
        
        # Per-second rate limiting
        time_since_last = current_time - self.last_request_time
        if time_since_last < (1.0 / self.requests_per_second):
            sleep_time = (1.0 / self.requests_per_second) - time_since_last
            time.sleep(sleep_time)
        
        # Per-minute rate limiting
        current_time = time.time()
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        if len(self.request_times) >= self.requests_per_minute:
            sleep_time = 60 - (current_time - self.request_times[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
                # Clean up old requests after sleeping
                current_time = time.time()
                self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        self.request_times.append(current_time)
        self.last_request_time = current_time

rate_limiter = RateLimiter(requests_per_minute=50, requests_per_second=1)

def describe_image_with_openai(image_bytes):
    url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('AIPROXY_TOKEN')}",
        "Content-Type": "application/json"
    }
    
    base64_data = image_bytes if image_bytes.startswith("iVBOR") else image_bytes.split(",")[-1]
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": [
                {"type": "text", "text": DESCRIBE_IMAGE_PROMPT},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64_data}}
            ]}
        ],
        "max_tokens": 256
    }

    for attempt in range(MAX_RETRIES):
        rate_limiter.wait_if_needed()
        try:
            response = httpx.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(2)
    
    return None

# def describe_image_with_openai(image_bytes):    
#     for attempt in range(MAX_RETRIES):
#         rate_limiter.wait_if_needed()
        
#         response = openai.chat.completions.create(model = "gpt-4o-mini",
#             messages=[
#                 {"role": "user", "content": [
#                     {"type": "text", "text": DESCRIBE_IMAGE_PROMPT},
#                     {"type": "image_url", "image_url": {"url": "data:image/png;base64," + image_bytes}}
#                 ]}
#             ],
#             max_tokens=256,
#         )

#     try:        
#         return response.choices[0].message.content.strip()
#     except Exception as e:
#         print(f"Error extracting description!!!")
#         return None

def describe_image_with_gemini(image_bytes):
    try:
        for attempt in range(MAX_RETRIES):
            rate_limiter.wait_if_needed()
            try:
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                result = client.models.generate_content(model="gemini-2.5-flash", contents=[DESCRIBE_IMAGE_PROMPT, image_bytes])
            except Exception as e:
                print(f"Gemini error on attempt {attempt + 1}: {e}")
                time.sleep(2)               
        return result.text.strip()

    except Exception as e:
        print(f"Gemini error: {e}")
        return None

def extract_posts_to_markdown(json_path, output_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    topic_url = lines[0].strip()
    topic_slug, _ = topic_url.split("/")
    json_data = json.loads("".join(lines[1:]))

    posts = json_data.get("post_stream", {}).get("posts", [])

    md_lines = [f"## {topic_slug.replace('-', ' ')}", f"{BASE_URL}/t/{topic_url}", "", ""]

    for post in posts:
        post_id = post.get("id")
        raw_html = post.get("cooked", "")
        soup = BeautifulSoup(raw_html, "html.parser")

        for img_tag in soup.find_all("img"):
            img_url = img_tag.get("src")
            if img_url:
                if "emoji.discourse-cdn.com" in img_url:
                    continue
                if "avatars.discourse-cdn.com" in img_url:
                    continue
                if "user_avatar" in img_url:
                    continue
                if "favicon" in img_url:
                    continue

                print("IMAGE CALL!!!")
                print(img_url)
                
                try:
                    img_response = requests.get(img_url)
                    img_response.raise_for_status()
                    img_b64 = base64.b64encode(img_response.content).decode('utf-8')
                    description = describe_image_with_openai(img_b64)
                    alt_text = f"```Image was here: {description}```"
                    img_tag.replace_with(alt_text)
                except Exception as e:
                    print(f"Failed to process image {img_url}: {e}")
                    img_tag.replace_with(f"[Image at {img_url}]")
                    

        text_content = soup.get_text(strip=False)
        md_lines.append(f"**Post ID:** {post_id}\n")
        md_lines.append(text_content.strip())
        md_lines.append("")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))

    print(f"Markdown file written to: {output_path}")


for json_file in Path("discourse_jsons").glob("*.json"):

    md_file = Path("discourse_md") / (json_file.stem + ".md")
    if not md_file.exists():
        print(f"Converting {json_file.name} to {md_file.name}...")
        extract_posts_to_markdown(json_file, md_file)
    else:
        print(f"{md_file.name} already exists. Skipping conversion.")

 