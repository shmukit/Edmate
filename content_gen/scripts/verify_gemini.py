import os
from google import genai
from dotenv import load_dotenv

# Load environment variables from content_gen/.env
load_dotenv('content_gen/.env')


def verify_gemini():
    project_id = "mcq-master-490011"
    location = "asia-south1"  # Default common location

    print(
        f"Loading credentials from: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")

    try:
        # Initialize client with Vertex AI support
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location
        )

        print("Checking models...")
        # Try a simple generation to verify connectivity
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Hello, are you connected?'
        )

        print(f"Response from Gemini: {response.text}")
        print("Verification SUCCESS.")

    except Exception as e:
        print(f"Error verifies Gemini: {e}")


if __name__ == "__main__":
    verify_gemini()
