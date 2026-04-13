from celery import Celery
from dotenv import load_dotenv
import asyncio
import redis
import os

load_dotenv()

celery_app = Celery(
    "code-review-agent",
    broker=REDIS_URL,
    backend=REDIS_URL
)

redis_client = redis.Redis(host="localhost", port=6379, db=0)

@celery_app.task(name="review_pr", autoretry_for=(Exception,), max_retries=3, default_retry_delay=10)
def review_pr(owner: str, repo: str, pull_number: int, head_sha: str):
    idempotency_key = f"reviewed:{owner}:{repo}:{head_sha}"
    if redis_client.exists(idempotency_key):
        print(f"Already reviewed commit {head_sha} — skipping")
        return

    print(f"Processing PR #{pull_number} for {owner}/{repo}")

    from app.github.service import get_pr_files, post_review
    from app.review.chunker import parse_patch_into_chunks
    from app.llm.service import review_chunk
    from app.db.database import SessionLocal
    from app.db.models import Review, Finding

    db = SessionLocal()

    # Create review record
    review = Review(
        owner=owner,
        repo=repo,
        pull_number=pull_number,
        head_sha=head_sha,
        status="pending"
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    async def run():
        files = await get_pr_files(owner, repo, pull_number)
        chunks = parse_patch_into_chunks(files)

        all_findings = []
        total_tokens_in = 0
        total_tokens_out = 0

        for chunk in chunks:
            print(f"Reviewing {chunk['filename']}...")
            try:
                findings, tokens_in, tokens_out = await review_chunk(chunk)
                total_tokens_in += tokens_in
                total_tokens_out += tokens_out
            except Exception as e:
                print(f"Failed to review {chunk['filename']}: {e}")
                continue

            for f in findings:
                line = f.get("line")
                position = chunk["position_map"].get(line)
                if position is None:
                    print(f"Skipping finding — line {line} not in position map")
                    continue
                f["filename"] = chunk["filename"]
                f["position"] = position
                all_findings.append(f)
                print(f"  [{f['severity'].upper()}] Line {line} (pos {position}): {f['message']}")

        print(f"Total valid findings: {len(all_findings)}")

        # Save findings to DB
        for f in all_findings:
            finding = Finding(
                review_id=review.id,
                filename=f["filename"],
                line=f["line"],
                severity=f["severity"],
                category=f["category"],
                message=f["message"],
                suggestion=f["suggestion"]
            )
            db.add(finding)

        # Update review record
        review.status = "completed"
        review.total_findings = len(all_findings)
        review.tokens_in = total_tokens_in
        review.tokens_out = total_tokens_out
        db.commit()

        await post_review(owner, repo, pull_number, head_sha, all_findings)
        print("Review posted to GitHub successfully")

    try:
        asyncio.run(run())
        redis_client.setex(idempotency_key, 60 * 60 * 24 * 7, "1")
    except Exception as e:
        review.status = "failed"
        db.commit()
        raise e
    finally:
        db.close()