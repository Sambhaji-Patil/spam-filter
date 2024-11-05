import joblib
import requests
import json
import os

GITHUB_API_URL = "https://api.github.com/graphql"

def fetch_comments(owner, repo, headers, after_cursor=None):
    query = """
    query($owner: String!, $repo: String!, $first: Int, $after: String) {
      repository(owner: $owner, name: $repo) {
        discussions(first: 1) {
          edges {
            node {
              id
              title
              comments(first: $first, after: $after) {
                edges {
                  node {
                    id
                    body
                    isMinimized
                  }
                  cursor
                }
                pageInfo {
                  endCursor
                  hasNextPage
                }
              }
            }
          }
          pageInfo{
            hasNextPage
            endCursor
          }
        }
      }
    }
    """
    variables = {
        "owner": owner,
        "repo": repo,
        "first": 10,
        "after": after_cursor,
    }
    response = requests.post(GITHUB_API_URL, headers=headers, json={"query": query, "variables": variables})
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Query failed with code {response.status_code}. Response: {response.json()}")

def minimize_comment(comment_id, headers):
    mutation = """
    mutation($commentId: ID!) {
      minimizeComment(input: {subjectId: $commentId, classifier: SPAM}) {
        minimizedComment {
          isMinimized
          minimizedReason
        }
      }
    }
    """
    variables = {
        "commentId": comment_id
    }
    response = requests.post(GITHUB_API_URL, headers=headers, json={"query": mutation, "variables": variables})
    if response.status_code == 200:
        data = response.json()
        return data["data"]["minimizeComment"]["minimizedComment"]["isMinimized"]
    else:
        print(f"Failed to minimize comment with ID {comment_id}. Status code: {response.status_code}")
        return False

def detect_spam(comment_body):
    model = joblib.load("spam_classifier_model.pkl")
    return model.predict([comment_body])[0] == 1

def moderate_comments(owner, repo, token):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    spam_results = []
    latest_cursor = None
    try:
        while True:
            data = fetch_comments(owner, repo, headers, latest_cursor)
            print(json.dumps(data, indent=2))

            for discussion in data['data']['repository']['discussions']['edges']:
                for comment_edge in discussion['node']['comments']['edges']:
                    comment_id = comment_edge['node']['id']
                    comment_body = comment_edge['node']['body']
                    is_minimized = comment_edge['node']['isMinimized']
                    
                    if not is_minimized:
                        if detect_spam(comment_body):
                            hidden = minimize_comment(comment_id, headers)
                            spam_results.append({"id": comment_id, "hidden": hidden})

                    latest_cursor = comment_edge['cursor']

                page_info = discussion['node']['comments']['pageInfo']
                if not page_info['hasNextPage']:
                    break

            if not data['data']['repository']['discussions']['pageInfo']['hasNextPage']:
                break
            latest_cursor = data['data']['repository']['discussions']['pageInfo']["endCursor"]
    
    except Exception as e:
        print("Error processing: " + str(e))
      
    print("Moderation Results:")
    print(json.dumps(spam_results, indent=4))

if __name__ == "__main__":
    OWNER = "Sambhaji-Patil"  # Replace with the repository owner
    REPO = "spam-filter"     # Replace with the repository name
    TOKEN = os.getenv('GITHUB_TOKEN')  # Ensure this is set in your GitHub Actions environment
    moderate_comments(OWNER, REPO, TOKEN)
