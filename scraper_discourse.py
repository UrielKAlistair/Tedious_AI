import os
import requests
import json

BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
COURSE_SLUG = "/c/courses/tds-kb/34.json"

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
    (created after the ending time, so cannot contain a relevant post, or the last post was made before the starting time)
    Remaining topics are potentially relevant, and their IDs are stored in a file. 
    (The only way it can not contain a relevant post is if topic was created long before the start time, 
    and all follow up posts wihin it made fall after the end time)
    These "interesting" topics will then be scanned for relevant posts.
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

def get_posts_in_topic(topic_url):
    '''
    Goes through every post within a topic, and filters it by time range. 
    Makes one single output file per topic. 
    Adds only the relevant posts to the final output. 
    Also includes the topic metadata at the top of the file.
    '''

    my_cookie = cookie_str_to_json(os.getenv("DISCOURSE_COOKIE"))
    session = requests.Session()
    session.cookies.update(my_cookie)

    url = f"{BASE_URL}/t/{topic_url}.json"
    response = session.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch topic {topic_url}: {response.status_code}")
        return None

def fetch_discourse_data():
    if not os.path.exists("discourse_jsons/relevant_topics.txt"):
        print("No relevant topics file found. Fetching relevant topics...")
        topics = get_relevant_topics()
        
    else:
        with open("discourse_jsons/relevant_topics.txt", "r") as f:
            lines = f.readlines()
            topics = [line.strip().split(",") for line in lines[1:] if line.strip()]

    for topic_url in topics:
        topic_slug, topic_id = topic_url.split("/")
        print(f"Fetching posts for topic {topic_slug.replace('-',' ')} (ID: {topic_id})...")
        if not os.path.exists(f"discourse_jsons/{topic_id}.json"):
            topic_details = get_posts_in_topic(topic_url)
            with open(f"discourse_jsons/{topic_id}.json", "w") as f:
                json.dump(topic_details, f)


def main():
    fetch_discourse_data()

if __name__ == "__main__":
    main()