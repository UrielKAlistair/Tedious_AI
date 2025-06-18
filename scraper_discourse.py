import os
import requests
import json

BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
COURSE_SLUG = "/c/courses/tds-kb/34.json"
POSTS_BATCH_SIZE = 50


def cookie_str_to_json(raw_cookie_string):
    cookies = {}
    for part in raw_cookie_string.strip().split(";"):
        if "=" in part:
            key, value = part.strip().split("=", 1)
            cookies[key] = value
    return cookies


def get_relevant_topics(start_time = "2025-01-01T00:00:00.000Z", end_time = "2025-04-15T00:00:00.000Z"):
    '''
    Goes through the topics created within the TDS course page, and elimates the ones that are not relevant to the time range specified.
    (topic was created after the ending time, so cannot contain a relevant post, or the last post in the topic was made before the starting time)
    Remaining topics are potentially relevant, and their IDs are stored in a file. 

    (The only way a topic passing this filter can **not** contain a relevant post is if the topic was created long before the start time, 
    and all follow up posts wihin it made fall after the end time, thereby having no posts in the required time range.)
    These "interesting" topics will then be scanned and if any of the posts in it are relevant, then the topic will be retained in the final pipeline.

    It was considered that the posts within topics only in the time range could be used, to follow the problem statement by the word, 
    but it doesn't make contextual sense to leave out the posts that these posts reply to, or the topic itself, 
    so the whole topic is being retained if any post within it falls in the requested time range.
    '''

    my_cookie = cookie_str_to_json(os.getenv("DISCOURSE_COOKIE"))
    session = requests.Session()
    session.cookies.update(my_cookie)
    relevant_topics = []
    page_no = 1

    while True:
        url = f"{BASE_URL}{COURSE_SLUG}?page={page_no}"
        page_data = session.get(url)
        page_no += 1
        topics = page_data.json()["topic_list"]["topics"]

        found_any = False
        all_before_start = True # Checks if we have reached distant past

        for topic in topics:
            if start_time <= topic["last_posted_at"]:
                all_before_start = False           
                if topic["created_at"] <= end_time:
                    relevant_topics.append(f'{topic["slug"]}/{topic["id"]}')
                    found_any = True
                
        if not found_any and all_before_start:
            break
            
    print(f"Found {len(relevant_topics)} relevant topics between {start_time} and {end_time}.")
    print("Made a total of", page_no-1, "requests to the Discourse API.")

    with open("discourse_jsons/relevant_topics.txt", "w") as f:
        f.write(f"{start_time} - {end_time}\n")
        for topic in relevant_topics:
            f.write(f"{topic}\n")

    return relevant_topics

def get_posts_in_topic(topic_url, start_time="2025-01-01T00:00:00.000Z", end_time="2025-04-15T00:00:00.000Z"):
    '''
    Fetches all posts in a Discourse topic given by `topic_url`.
    Discards the topic if none of its posts fall within a desired time range.
    Makes one single output file per topic. 
    Also includes the topic metadata at the top of the file.
    '''

    _, topic_id = topic_url.split("/")
    session = requests.Session()
    session.cookies.update(cookie_str_to_json(os.getenv("DISCOURSE_COOKIE")))

    try:
        response = session.get(f"{BASE_URL}/t/{topic_url}.json", timeout=30)
        response.raise_for_status()
        topic_data = response.json()
    except Exception as e:
        print(f"Failed to fetch topic {topic_id}: {e}")
        return None

    post_stream = topic_data.get("post_stream", {})
    stream_ids = post_stream.get("stream", [])
    loaded_posts = post_stream.get("posts", [])

    loaded_ids = {p["id"] for p in loaded_posts if "id" in p}
    missing_ids = [pid for pid in stream_ids if pid not in loaded_ids]

    print(f"Topic {topic_id}: Total posts = {len(stream_ids)}, Loaded = {len(loaded_ids)}, Missing = {len(missing_ids)}")

    # Fetch missing posts
    additional_posts = []
    for i in range(0, len(missing_ids), POSTS_BATCH_SIZE):
        batch_ids = missing_ids[i:i + POSTS_BATCH_SIZE]
        params = [("post_ids[]", pid) for pid in batch_ids]
        batch_url = f"{BASE_URL}/t/{topic_id}/posts.json"

        try:
            batch_resp = session.get(batch_url, params=params, timeout=60)
            batch_resp.raise_for_status()
            batch_data = batch_resp.json()

            if isinstance(batch_data, list):
                additional_posts.extend(batch_data)
            elif "post_stream" in batch_data and "posts" in batch_data["post_stream"]:
                additional_posts.extend(batch_data["post_stream"]["posts"])
            elif "posts" in batch_data:
                additional_posts.extend(batch_data["posts"])
            else:
                print(f"Topic {topic_id}: Unexpected JSON in post batch: {str(batch_data)[:200]}...")
        except Exception as e:
            print(f"Failed to fetch batch for topic {topic_id} (IDs: {batch_ids}): {e}")

    if additional_posts:
        print(f"Topic {topic_id}: Fetched {len(additional_posts)} more posts.")
        id_to_post = {p["id"]: p for p in loaded_posts}
        for post in additional_posts:
            id_to_post[post["id"]] = post

        # Sort all posts by stream order
        sorted_posts = [id_to_post[pid] for pid in stream_ids if pid in id_to_post]
        topic_data["post_stream"]["posts"] = sorted_posts

    def in_range(post):
        return start_time <= post["created_at"] <= end_time
       
    if not any(in_range(p) for p in topic_data["post_stream"]["posts"]):
        print(f"Topic {topic_id}: No posts in desired time range. Discarding.")
        return None

    print(f"Topic {topic_id}: Final post count = {len(topic_data['post_stream']['posts'])}")
    return topic_data


def fetch_discourse_data():
    if not os.path.exists("discourse_jsons/relevant_topics.txt"):
        print("No relevant topics file found. Fetching relevant topics...")
        topics = get_relevant_topics()
        
    else:
        with open("discourse_jsons/relevant_topics.txt", "r") as f:
            lines = f.readlines()
            topics = [line.strip() for line in lines[1:] if line.strip()]

    for topic_url in topics:
        topic_slug, topic_id = topic_url.split("/")
        print(f"Fetching posts for topic {topic_slug.replace('-',' ')} (ID: {topic_id})...")
        if not os.path.exists(f"discourse_jsons/{topic_id}.json"):
            topic_details = get_posts_in_topic(topic_url)
            if topic_details is None:
                print(f"Skipping topic {topic_id} due to no relevant posts.")
                continue

            with open(f"discourse_jsons/{topic_id}.json", "w") as f:
                f.write(f"{topic_url}\n")
                json.dump(topic_details, f)


def main():
    fetch_discourse_data()

if __name__ == "__main__":
    main()