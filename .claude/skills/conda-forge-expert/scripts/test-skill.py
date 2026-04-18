import requests

def test_api():
    url = "https://api.anaconda.org/package/conda-forge/pillow"
    resp = requests.get(url)
    print(resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        print(f"Name: {data.get('name')}")
        print(f"Versions: {len(data.get('versions'))}")

test_api()