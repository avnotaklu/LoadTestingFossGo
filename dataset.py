import json
import requests
import os

base_url = os.environ["BASE_URL"]


def get_headers():
    headers = {
        "Content-Type": "application/json",
    }
    return headers


def main():
    data: list[dict] = []
    url = f"https://${base_url}/Authentication/PasswordSignUp"

    for i in range(100, 1000):
        try:
            data = {
                "username": f"p_{i}",
                "password": "string",
                "googleSignIn": False,
            }
            response = requests.post(url, json=data, headers=get_headers())
            print("User Sign Up: ", response.json())
        except Exception as e:
            print(e)


if __name__ == "__main__":
    main()
