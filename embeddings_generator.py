# vector_embedding: [chunk of text, topic_url, post_id] 
# Given an input, find the top 10 closest vector embeddings and return their chunks, their topic and post urls.
# Aggregate all the topic urls in code, so that you have topic url: chunk1 posturl chunk2 topic2 url and so on. 
# Ask the LLM to output the topic url and the post url of relevant chunks as {links:""}. 
# Even if chunks are not too relevant, some link should be there, to say this is the closest thing we have found.
# Link app.py to call the function in this file.