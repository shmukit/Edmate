#!/usr/bin/env python3
"""
Blob Storage Upload Script
Uploads extracted PNG images to Azure Blob Storage
Generates CDN URL mappings for database import
"""
import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from azure.core.credentials import AzureNamedKeyCredential
from azure.storage.blob import BlobServiceClient, ContentSettings


def _account_name_from_conn_str(conn: str) -> Optional[str]:
    """Parse AccountName from an Azure storage connection string."""
    for seg in conn.split(";"):
        seg = seg.strip()
        if seg.lower().startswith("accountname="):
            return seg.split("=", 1)[1].strip()
    return None


class StorageUploader:
    def __init__(self):
        """
        Initialize storage uploader with Azure Blob Storage
        """
        self.client, self._blob_account_name = self._init_client()

    def _init_client(self) -> Tuple[BlobServiceClient, str]:
        """Initialize client; return (client, storage account name for public URLs)."""
        account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()

        if conn:
            client = BlobServiceClient.from_connection_string(conn)
            resolved = (account_name or "").strip() or _account_name_from_conn_str(conn) or ""
            if not resolved:
                raise ValueError(
                    "Set AZURE_STORAGE_ACCOUNT_NAME, or include AccountName= in "
                    "AZURE_STORAGE_CONNECTION_STRING, so public blob URLs can be built."
                )
            return client, resolved

        if not account_name or not account_key:
            raise ValueError(
                "Missing Azure credentials. Set AZURE_STORAGE_CONNECTION_STRING, or "
                "both AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY."
            )

        name = account_name.strip()
        key = account_key.strip()
        # Named key credential — avoids a connection-string literal in source
        # (scanners flag AccountKey= substrings in repository code).
        credential = AzureNamedKeyCredential(name, key)
        account_url = f"https://{name}.blob.core.windows.net"
        return BlobServiceClient(account_url=account_url, credential=credential), name

    def upload_file(self, local_path: str, container: str, key: str, retries: int = 3) -> str:
        """
        Upload a single file to Azure Blob Storage with retry logic

        Args:
            local_path: Path to local file
            container: Storage container name
            key: Object key (path in container)
            retries: Number of retry attempts

        Returns:
            CDN URL of uploaded file
        """
        for attempt in range(retries):
            try:
                # Azure Blob Storage upload
                blob_client = self.client.get_blob_client(
                    container=container, blob=key)
                with open(local_path, "rb") as data:
                    blob_client.upload_blob(
                        data,
                        overwrite=True,
                        content_settings=ContentSettings(
                            content_type='image/png')
                    )

                # Generate CDN URL
                cdn_url = self._generate_cdn_url(container, key)
                return cdn_url

            except Exception as e:
                if attempt == retries - 1:
                    raise Exception(
                        f"Failed to upload {local_path} after {retries} attempts: {e}")
                print(f"⚠️  Upload attempt {attempt + 1} failed, retrying...")
        raise RuntimeError(f"Upload failed unexpectedly for {local_path}")

    def _generate_cdn_url(self, container: str, key: str) -> str:
        """Generate public CDN URL for uploaded file"""
        custom_cdn = os.getenv("AZURE_STORAGE_CDN_URL")

        if custom_cdn:
            return f"{custom_cdn}/{container}/{key}"
        return (
            f"https://{self._blob_account_name}.blob.core.windows.net/{container}/{key}"
        )

    def upload_directory(
        self,
        images_dir: str,
        container: str,
        base_path: str = "diagrams"
    ) -> Tuple[Dict[str, str], Dict]:
        """
        Upload all PNG files in a directory to Azure Blob Storage

        Args:
            images_dir: Directory containing PNG files
            container: Storage container name
            base_path: Path prefix in container (e.g., "diagrams/9701_s25_qp_13")

        Returns:
            Tuple of (cdn_mapping, report)
            - cdn_mapping: {filename: cdn_url}
            - report: {total, uploaded, failed, errors}
        """
        images_path = Path(images_dir)
        png_files = list(images_path.glob("*.png"))

        cdn_mapping = {}
        errors = []
        uploaded_count = 0

        print(f"📤 Uploading {len(png_files)} images to Azure Blob Storage...")

        for img_path in png_files:
            try:
                key = f"{base_path}/{img_path.name}"
                cdn_url = self.upload_file(str(img_path), container, key)
                cdn_mapping[img_path.name] = cdn_url
                uploaded_count += 1
                print(f"  ✅ {img_path.name} → {cdn_url}")

            except Exception as e:
                errors.append({"file": img_path.name, "error": str(e)})
                print(f"  ❌ {img_path.name}: {e}")

        report = {
            "total": len(png_files),
            "uploaded": uploaded_count,
            "failed": len(errors),
            "errors": errors
        }

        print(
            f"\n✅ Upload complete: {uploaded_count}/{len(png_files)} successful")

        return cdn_mapping, report


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Upload images to Azure Blob Storage")
    parser.add_argument("images_dir", help="Directory containing PNG images")
    parser.add_argument("--container", required=True,
                        help="Azure Storage container name")
    parser.add_argument("--base-path", default="diagrams",
                        help="Base path in container")
    parser.add_argument("--output", help="Output JSON file for CDN mapping")

    args = parser.parse_args()

    # Upload
    uploader = StorageUploader()
    cdn_mapping, report = uploader.upload_directory(
        images_dir=args.images_dir,
        container=args.container,
        base_path=args.base_path
    )

    # Save CDN mapping
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump({
                "cdn_mapping": cdn_mapping,
                "report": report
            }, f, indent=2)

        print(f"\n💾 CDN mapping saved to: {output_path}")

    # Exit with error code if any uploads failed
    sys.exit(0 if report["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
