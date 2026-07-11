import getpass
import json
import argparse
import sys
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a Gemini API key.")
    parser.add_argument("--model", default="gemini-3.5-flash")
    args = parser.parse_args()

    key = getpass.getpass("Paste Gemini API key: ").strip()
    if not key:
        print("No key provided.")
        return 1

    payload = {
        "model": args.model,
        "messages": [
            {
                "role": "user",
                "content": "Reply with exactly: gemini-ok",
            }
        ],
    }
    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print("HTTP %s" % exc.code)
        print(body[:1000])
        return 1
    except Exception as exc:
        print("Request failed: %s" % exc)
        return 1

    content = data["choices"][0]["message"]["content"]
    print(content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
