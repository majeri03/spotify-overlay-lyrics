import requests

def translate_gtx(text: str, target_lang: str = "id") -> str:
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": target_lang,
        "dt": "t",
        "q": text
    }
    r = requests.get(url, params=params, timeout=5).json()
    if r and r[0]:
        return "".join(sentence[0] for sentence in r[0] if sentence and sentence[0])
    return text

sample_lines = [
    "You got me thinking 'bout when you were mine",
    "And I snuck in through the garden gate",
    "Every night that summer just to seal my fate",
    "I found a love for me"
]

print("=== Testing Google Translate GTX ===")
for line in sample_lines:
    tr = translate_gtx(line, "id")
    print(f"EN: {line}")
    print(f"ID: {tr}\n")
