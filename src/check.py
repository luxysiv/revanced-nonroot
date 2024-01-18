import requests

def download_release_body(repo_owner, repo_name, access_token=None):
    headers = {}
    
    if access_token:
        headers['Authorization'] = f"Bearer {access_token}"

    release_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
    release_data = requests.get(release_url, headers=headers).json()
    
    return release_data.get('body', '')

def check_release_body(script_repo_body, downloaded_patch_file_name):
    return script_repo_body != downloaded_patch_file_name
  
