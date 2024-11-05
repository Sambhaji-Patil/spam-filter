from database import *
import joblib
import requests
import json
import os

GITHUB_API_URL = "https://api.github.com/graphql"

def fetch_comments(owner, repo, headers, after_cursor=None, lastpage=''):
    query = """
    query($owner: String!, $repo: String!, $first: Int, $after: String, $lastpage: String) {
      repository(owner: $owner, name: $repo) {
        discussions(first: 1, after: $lastpage) {
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
        "lastpage": lastpage,
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
    model = joblib.load("models/spam_detector_model.pkl")
    return model.predict([comment_body])[0] == 1

def moderate_discussion_comments(repo_id):
    repo_id, owner, repo, token, last_processed_cursor, a, b = fetch_repository_by_id(repo_id)
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    spam_results = []
    latest_cursor = last_processed_cursor
    lastpage = ''
    try:
        while True:
            latest_cursor = last_processed_cursor
            comments_remaining = True
            while comments_remaining:
                data = fetch_comments(owner, repo, headers, latest_cursor, lastpage)
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
                        comments_remaining = False

                if not data['data']['repository']['discussions']['edges']:
                    break

            if not data['data']['repository']['discussions']['pageInfo']['hasNextPage']:
                break
            lastpage = data['data']['repository']['discussions']['pageInfo']["endCursor"]
    
    except Exception as e:
        print("Error processing: " + str(e))
      
    print("Moderation Results:")
    print(json.dumps(spam_results, indent=4))

    update_discussion_cursor(repo_id, latest_cursor)

if __name__ == "__main__":
    moderate_discussion_comments(1)
