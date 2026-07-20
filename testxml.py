import requests

url = "https://cwd.relaticsonline.com/DataExchange/210b2918-b359-4892-a23b-bf96ad23d82f/icons"

headers = {f"authorization": "Bearer {token}"}

response = requests.get(url, headers=headers)

print(response.text)