import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


def setup_opik():
    try:
        import opik
        from opik import Opik
        from opik.configurator.configure import configure
    except ImportError:
        print("❌ Opik SDK not installed. Run: pip install opik")
        return

    api_key = os.getenv("OPIK_API_KEY")
    project_name = os.getenv("OPIK_PROJECT_NAME", "Edmate")

    if not api_key:
        print("❌ OPIK_API_KEY not found in .env file.")
        return

    print(f"🚀 Configuring Opik for project: {project_name}...")

    # Configure the environment
    configure(api_key=api_key, force=True, automatic_approvals=True)

    # Explicitly create project
    client = Opik()
    try:
        # Check if project exists or create it
        client.rest_client.projects.create_project(name=project_name)
        print(f"✅ Project '{project_name}' initialized successfully in Opik!")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"✅ Project '{project_name}' already exists.")
        else:
            print(f"⚠️ Note on project creation: {e}")

    print("\n🎉 Opik is ready! You can now view your traces at: https://www.comet.com/opik/")


if __name__ == "__main__":
    setup_opik()
