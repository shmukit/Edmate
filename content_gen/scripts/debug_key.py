import json
from cryptography.hazmat.primitives import serialization
from google.oauth2 import service_account


def debug_key():
    with open("credentials/gemini_creds.json", "r") as f:
        data = json.load(f)

    key_str = data["private_key"]
    print(f"Key string starts with: {repr(key_str[:50])}")
    print(f"Key string ends with: {repr(key_str[-50:])}")

    try:
        # Attempt to load the key using cryptography
        serialization.load_pem_private_key(
            key_str.encode("utf-8"), password=None)
        print("Success: Key is valid PEM.")
    except Exception as e:
        print(f"Failure: Key is NOT valid PEM. Error: {e}")

        # Try to clean it up
        # Remove extra whitespace/newlines at start/end
        cleaned_key = key_str.strip()
        # Ensure it has exactly one newline after header and before footer
        # Actually PEM is quite flexible, but let's try standardizing it.

        lines = cleaned_key.split("\n")
        header = lines[0]
        footer = lines[-1]
        data_body = "\n".join(lines[1:-1])

        final_key = f"{header}\n{data_body}\n{footer}\n"

        try:
            serialization.load_pem_private_key(
                final_key.encode("utf-8"), password=None)
            print("Cleanup Success: Key is now valid.")
            data["private_key"] = final_key
            with open("credentials/gemini_creds.json", "w") as f:
                json.dump(data, f, indent=2)
            print("Updated gemini_creds.json.")
        except Exception as e2:
            print(f"Cleanup Failure: {e2}")


if __name__ == "__main__":
    debug_key()
