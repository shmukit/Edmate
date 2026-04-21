import json
import os
import psycopg2
from pathlib import Path


def update_db_images():
    # Paths
    extracted_json = "content_gen/content_gen/data/extracted/9701_w25_qp_11_extracted.json"
    cdn_json = "content_gen/data/9701_w25_qp_11_cdn.json"
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        print("❌ DATABASE_URL not set.")
        return

    # Load data
    with open(extracted_json, 'r') as f:
        extracted_data = json.load(f)

    with open(cdn_json, 'r') as f:
        cdn_data = json.load(f)
        cdn_mapping = cdn_data.get("cdn_mapping", {})

    print(f"📊 Loaded {len(cdn_mapping)} CDN mappings.")

    # Connect to DB
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        updated_count = 0
        skipped_count = 0

        for q in extracted_data.get("questions", []):
            q_num = q.get("question_number")
            paper_code = "9701_w25_qp_11"
            q_identifier = f"{paper_code}/Q{q_num}"

            # Collect all images (stem + options)
            image_filenames = []
            # In the extracted JSON, stem_images contains relative paths
            for img_path in q.get("stem_images", []):
                image_filenames.append(Path(img_path).name)

            # Option images
            opt_images = q.get("option_images", {})
            if isinstance(opt_images, dict):
                for opt, imgs in opt_images.items():
                    for img_path in imgs:
                        image_filenames.append(Path(img_path).name)

            if not image_filenames:
                skipped_count += 1
                continue

            # Map to CDN URLs
            cdn_urls = []
            for fname in image_filenames:
                if fname in cdn_mapping:
                    cdn_urls.append(cdn_mapping[fname])
                else:
                    print(
                        f"  ⚠️  Missing mapping for {fname} in {q_identifier}")

            if not cdn_urls:
                skipped_count += 1
                continue

            # Join with newline as required by the frontend
            other_contents = "\n".join(cdn_urls)

            # Update DB
            cur.execute(
                "UPDATE chemistry_questions SET other_contents = %s WHERE question_identifier = %s",
                (other_contents, q_identifier)
            )
            updated_count += 1
            print(f"  ✅ Updated {q_identifier} with {len(cdn_urls)} images.")

        conn.commit()
        print(
            f"\n✨ Successfully updated {updated_count} questions. Skipped {skipped_count} questions.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Database error: {e}")


if __name__ == "__main__":
    update_db_images()
