import pickle
import sys
import requests
from os import getenv

# Load the `.pkl` model from the workflow directory
with open('spam_detector_model.pkl', 'rb') as model_file:
    model = pickle.load(model_file)

def is_spam(comment_text):
    # Use the model to predict if the comment is spam (assuming the model has a `predict` method)
    return model.predict([comment_text])[0] == 'spam'

def hide_comment(comment_id, comment_url):
    token = getenv('GITHUB_TOKEN')
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    hide_url = f"{comment_url}/reactions"
    response = requests.post(
        hide_url,
        headers=headers,
        json={"content": "🚫"}  # GitHub's API uses this emoji to hide a comment
    )
    return response.status_code == 201

if __name__ == "__main__":
    comment_text = sys.argv[1]
    comment_id = sys.argv[2]
    comment_url = sys.argv[3]

    if is_spam(comment_text):
        if hide_comment(comment_id, comment_url):
            print(f"Comment {comment_id} has been hidden as spam.")
        else:
            print(f"Failed to hide comment {comment_id}.")
    else:
        print("Comment is not spam.")
