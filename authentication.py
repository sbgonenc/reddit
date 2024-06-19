import os
import praw
from prawcore.exceptions import ResponseException
import toml


def get_reddit_config(config_file_path):
    if os.path.exists(config_file_path):
        return toml.load(config_file_path)["reddit"]
    return None


def authenticate_reddit(config=None, **kwargs):
    config = {
        "creds": {
            "client_id": kwargs.get("client_id", None),
            "client_secret": kwargs.get("client_secret", None),
            "username": kwargs.get("username", None),
            "password": kwargs.get("password", None),
            "2fa": kwargs.get("2fa", False),
    }} if config is None else config

    if config["creds"]["2fa"]:
        print("\nEnter your two-factor authentication code from your authenticator app.\n")
        code = input("> ")
        print()
        pw = config["creds"]["password"]
        passkey = f"{pw}:{code}"
    else:
        passkey = os.getenv("REDDIT_PASS", config["creds"]["password"])

    username = os.getenv("REDDIT_USER", config["creds"]["username"])
    if str(username).casefold().startswith("u/"):
        username = username[2:]
    try:
        reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT", config["creds"]["client_id"]),
            client_secret=os.getenv("REDDIT_SECRET", config["creds"]["client_secret"]),
            user_agent="Accessing Reddit threads",
            username=username,
            passkey=passkey,
            check_for_async=False,
            ratelimit_seconds=60, ## manually added ratelimit_seconds
        )
    except ResponseException as e:
        if e.response.status_code == 401:
            print("Invalid credentials - please check them in config.toml")
    except:
        print("Something went wrong...")

    return reddit