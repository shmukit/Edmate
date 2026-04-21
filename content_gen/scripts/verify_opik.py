import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


def verify_opik():
    try:
        import opik
        from opik import Opik, track
    except ImportError:
        print("❌ Opik SDK not installed.")
        return

    # Opik uses these env vars automatically
    api_key = os.getenv("OPIK_API_KEY")
    project_name = os.getenv("OPIK_PROJECT_NAME", "Edmate")

    if not api_key:
        print("❌ OPIK_API_KEY not found.")
        return

    print(f"📡 Testing Opik connection for project: {project_name}...")

    @track(project_name=project_name)
    def test_function():
        return "Connection successful"

    try:
        result = test_function()
        print(f"✅ Trace sent! Result: {result}")
        print("🔗 Check your dashboard: https://www.comet.com/opik/")
    except Exception as e:
        print(f"❌ Failed to send trace: {e}")


if __name__ == "__main__":
    verify_opik()
