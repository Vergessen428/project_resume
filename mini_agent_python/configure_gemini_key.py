import getpass
import os
import sys


DEFAULTS = {
    "GEMINI_MODEL": "gemini-3.1-flash-lite",
    "GEMINI_OPENAI_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai",
}


def main() -> int:
    project_root = os.path.realpath(os.path.dirname(__file__))
    env_path = os.path.join(project_root, ".env")
    key = getpass.getpass("Paste Gemini API key: ").strip()

    if not key:
        print("No key provided.")
        return 1

    values = {}
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                values[name.strip()] = value.strip()

    values["GEMINI_API_KEY"] = key
    for name, value in DEFAULTS.items():
        values.setdefault(name, value)

    ordered_names = ["GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_OPENAI_BASE_URL"]
    with open(env_path, "w", encoding="utf-8") as f:
        for name in ordered_names:
            f.write("%s=%s\n" % (name, values[name]))

    print("Gemini config saved to mini_agent_python/.env")
    return 0


if __name__ == "__main__":
    sys.exit(main())
