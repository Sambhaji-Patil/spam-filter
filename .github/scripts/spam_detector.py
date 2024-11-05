import joblib
import sys
import requests
from os import getenv
import re

# Load the model and vectorizer from the repository
model = joblib.load('spam_classifier_model.pkl')
vectorizer = joblib.load('vectorizer.pkl')

def preprocess_text(text):
    # Convert to lowercase and remove special characters
    text = text.lower()
    text = re.sub(r'\W', ' ', text)
    return text

def is_spam(comment_text):
    # Preprocess the comment text
    processed_text = preprocess_text(comment_text)
    
    # Vectorize the processed text
    message_vectorized = vectorizer.transform([processed_text])
    
    # Use the model to predict if the comment is spam
    return model.predict(message_vectorized)[0] == 1  # Return True if spam

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
