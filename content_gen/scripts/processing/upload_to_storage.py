#!/usr/bin/env python3
"""
Blob Storage Upload Script
Uploads extracted PNG images to Cloudflare R2 or AWS S3
Generates CDN URL mappings for database import
"""
import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import boto3
from botocore.exceptions import ClientError

class StorageUploader:
    def __init__(self, provider: str = "r2"):
        """
        Initialize storage uploader
        
        Args:
            provider: "r2" for Cloudflare R2, "s3" for AWS S3
        """
        self.provider = provider
        self.client = self._init_client()
        
    def _init_client(self):
        """Initialize boto3 client for R2 or S3"""
        if self.provider == "r2":
            # Cloudflare R2 configuration
            account_id = os.getenv("R2_ACCOUNT_ID")
            access_key = os.getenv("R2_ACCESS_KEY_ID")
            secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
            
            if not all([account_id, access_key, secret_key]):
                raise ValueError("Missing R2 credentials. Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY")
            
            return boto3.client(
                's3',
                endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name='auto'
            )
        
        elif self.provider == "s3":
            # AWS S3 configuration
            access_key = os.getenv("AWS_ACCESS_KEY_ID")
            secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            region = os.getenv("AWS_REGION", "us-east-1")
            
            if not all([access_key, secret_key]):
                raise ValueError("Missing S3 credentials. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
            
            return boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
        
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'r2' or 's3'")
    
    def upload_file(self, local_path: str, bucket: str, key: str, retries: int = 3) -> str:
        """
        Upload a single file to storage with retry logic
        
        Args:
            local_path: Path to local file
            bucket: Storage bucket name
            key: Object key (path in bucket)
            retries: Number of retry attempts
            
        Returns:
            CDN URL of uploaded file
        """
        for attempt in range(retries):
            try:
                self.client.upload_file(
                    Filename=local_path,
                    Bucket=bucket,
                    Key=key,
                    ExtraArgs={'ACL': 'public-read', 'ContentType': 'image/png'}
                )
                
                # Generate CDN URL
                cdn_url = self._generate_cdn_url(bucket, key)
                return cdn_url
                
            except ClientError as e:
                if attempt == retries - 1:
                    raise Exception(f"Failed to upload {local_path} after {retries} attempts: {e}")
                print(f"⚠️  Upload attempt {attempt + 1} failed, retrying...")
        
    def _generate_cdn_url(self, bucket: str, key: str) -> str:
        """Generate public CDN URL for uploaded file"""
        if self.provider == "r2":
            # Use custom domain if configured, otherwise R2 public URL
            public_url = os.getenv("R2_PUBLIC_URL", f"https://pub-{bucket}.r2.dev")
            return f"{public_url}/{key}"
        
        elif self.provider == "s3":
            region = os.getenv("AWS_REGION", "us-east-1")
            return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
    
    def upload_directory(
        self, 
        images_dir: str, 
        bucket: str, 
        base_path: str = "diagrams"
    ) -> Tuple[Dict[str, str], Dict]:
        """
        Upload all PNG files in a directory
        
        Args:
            images_dir: Directory containing PNG files
            bucket: Storage bucket name
            base_path: Path prefix in bucket (e.g., "diagrams/9701_s25_qp_13")
            
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
        
        print(f"📤 Uploading {len(png_files)} images to {self.provider.upper()}...")
        
        for img_path in png_files:
            try:
                key = f"{base_path}/{img_path.name}"
                cdn_url = self.upload_file(str(img_path), bucket, key)
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
        
        print(f"\n✅ Upload complete: {uploaded_count}/{len(png_files)} successful")
        
        return cdn_mapping, report


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload images to cloud storage")
    parser.add_argument("images_dir", help="Directory containing PNG images")
    parser.add_argument("--provider", choices=["r2", "s3"], default="r2", help="Storage provider")
    parser.add_argument("--bucket", required=True, help="Storage bucket name")
    parser.add_argument("--base-path", default="diagrams", help="Base path in bucket")
    parser.add_argument("--output", help="Output JSON file for CDN mapping")
    
    args = parser.parse_args()
    
    # Upload
    uploader = StorageUploader(provider=args.provider)
    cdn_mapping, report = uploader.upload_directory(
        images_dir=args.images_dir,
        bucket=args.bucket,
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
