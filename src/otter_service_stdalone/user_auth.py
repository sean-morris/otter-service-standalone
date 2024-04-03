import json
import os
from otter_service_stdalone import fs_logging as log, access_sops_keys
import requests
import tornado
import urllib.parse


log_coll = f'{os.environ.get("ENVIRONMENT")}-debug'
environment_name = os.environ.get("ENVIRONMENT").split("-")[-1]
gh_key_path = os.path.join(os.path.dirname(__file__), f"secrets/gh_key.{environment_name}.yaml")
github_id = access_sops_keys.get(None, "github_access_id", secrets_file=gh_key_path)
github_secret = access_sops_keys.get(None, "github_access_secret", secrets_file=gh_key_path)


async def handle_authorization(form, state):
    """authorizes via oauth app token access github auth api

    Parameters:
        - form (tornado.web.RequestHandler): The request handler used to re-direct for
          authorization. The redirect url is configured at the github endpoint for the app
        - state (int): random uuid4 number generated to ensure communication between endpoints is
          not compromised
    """
    log.write_logs("Auth Workflow", "UserAuth: Get: Authorizing", "", "info", log_coll)
    q_params = f"client_id={github_id}&state={state}&scope=read:org"
    form.redirect(f'https://github.com/login/oauth/authorize?{q_params}')


async def get_acess_token(arg_state, state, code):
    """requests and returns the access token or None

    Parameters:
        - arg_state (int): the state argument being passed on the url string; this will be compared
          to the state value generated in this file to ensure they are the same!
        - state (int): random uuid4 number generated to ensure communication between endpoints is
          not compromised
        - code (str): the code that is returned from the authorization request

    Returns:
        - str: the access token used for subsequent calls to the api; or None
    """
    http_client = tornado.httpclient.AsyncHTTPClient()
    params = {
        'client_id': github_id,
        'client_secret': github_secret,
        'code': code,
        'redirect_uri': f"{os.environ.get('GRADER_DNS')}/oauth_callback"
    }
    m = "UserAuth: GitHubOAuthHandler: Getting Access Token"
    log.write_logs("Auth Workflow", m, "", "info", log_coll)
    response = await http_client.fetch(
        'https://github.com/login/oauth/access_token',
        method='POST',
        headers={'Accept': 'application/json'},
        body=urllib.parse.urlencode(params)
    )
    resp = json.loads(response.body.decode())
    access_token = resp['access_token']
    if arg_state != state:
        access_token = None
        m = "UserAuth: GitHubOAuthHandler: Cross-Site Forgery possible - aborting"
        log.write_logs("Auth Workflow", m, "", "info", log_coll)
    else:
        m = "UserAuth: GitHubOAuthHandler: Access Token Granted"
        log.write_logs("Auth Workflow", m, "", "info", log_coll)
    return access_token


async def handle_is_org_member(access_token, user):
    """the final authorization is to make sure the member has access to the application by being
    a part of the correct organizaton

    Parameters:
        - access_token (str): The OAuth access token.
        - user (str): the authenticated GitHub user name

    Returns:
        - boolean: True user is in the GH org, False otherwise
    """
    log.write_logs("Auth Workflow", "UserAuth: Get: Check Membership", "", "info", log_coll)
    if user:
        org_name = os.environ.get("AUTH_ORG")
        url = f'https://api.github.com/orgs/{org_name}/members/{user}'
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json',
        }
        response = requests.get(url, headers=headers)
        return response.status_code == 204
    else:
        return False


async def get_github_username(access_token):
    """
    Retrieve the GitHub username of the authenticated user.

    Parameters:
    - access_token (str): The OAuth access token.

    Returns:
    - str: The username of the authenticated user, or None if not found.
    """
    url = 'https://api.github.com/user'
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github.v3+json',
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        m = "UserAuth: Get: UserName - Success"
        log.write_logs("Auth Workflow", m, "", "info", log_coll)
        user_info = response.json()
        return user_info.get('login')
    else:
        m = f"UserAuth: Get: UserName - Fail:{response.status_code}"
        log.write_logs("Auth Workflow", m, "", "info", log_coll)
        return None
