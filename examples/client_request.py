import argparse
import os
import time
from pathlib import Path

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit any PDF to Edmate extract API and poll job status."
    )
    parser.add_argument(
        "--api-base-url",
        default="http://localhost:8000/api/v1",
        help="Base URL for the Edmate v1 API.",
    )
    parser.add_argument(
        "--pdf-path",
        required=True,
        help="Path to the input PDF to process.",
    )
    parser.add_argument(
        "--curriculum",
        default="General",
        help="Curriculum label sent to API.",
    )
    parser.add_argument(
        "--subject",
        default="General",
        help="Subject label sent to API.",
    )
    parser.add_argument(
        "--api-key-header",
        default="X-API-Key",
        help="Header name used for BYOK (example: X-API-Key, X-Gemini-Key, X-OpenAI-Key).",
    )
    parser.add_argument(
        "--api-key-env",
        default="LITELLM_API_KEY",
        help="Environment variable name that stores the BYOK key.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=5,
        help="Polling interval for job status.",
    )
    return parser.parse_args()


def process_document(args: argparse.Namespace) -> None:
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"Starting extraction for: {pdf_path}")

    headers = {}
    api_key = os.getenv(args.api_key_env)
    if api_key:
        headers[args.api_key_header] = api_key

    with pdf_path.open("rb") as f:
        response = requests.post(
            f"{args.api_base_url}/extract",
            files={"file": f},
            data={"curriculum": args.curriculum, "subject": args.subject},
            headers=headers,
            timeout=120,
        )

    if response.status_code != 200:
        raise RuntimeError(f"Extract request failed [{response.status_code}]: {response.text}")

    job_id = response.json()["job_id"]
    print(f"Job created: {job_id}")

    while True:
        status_res = requests.get(f"{args.api_base_url}/jobs/{job_id}", timeout=60)
        data = status_res.json()
        status = data.get("status")
        print(f"Current status: {status}")

        if status == "COMPLETED":
            questions = data.get("questions", [])
            print(f"Completed. Questions extracted: {len(questions)}")
            for idx, question in enumerate(questions, start=1):
                question_text = question.get("question_text", "")
                core = question.get("explanations", {}).get("core_concept", "")
                print(f"{idx}. {question_text}")
                if core:
                    print(f"   Core concept: {core}")
            return

        if status == "FAILED":
            raise RuntimeError(f"Processing failed: {data.get('error')}")

        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    process_document(parse_args())
