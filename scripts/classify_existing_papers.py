"""
Classify Existing Papers into Domains

Classifies all papers in the database into the domain taxonomy.

Usage:
    python scripts/classify_existing_papers.py [--method METHOD] [--limit LIMIT]

Options:
    --method: Classification method (keyword, llm, hybrid) [default: hybrid]
    --limit: Maximum papers to classify (0 = all) [default: 0]
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from tools.domain_classifier import DomainClassifier
from anthropic import Anthropic
import os
from dotenv import load_dotenv


def classify_existing_papers(method: str = "hybrid", limit: int = 0):
    """
    Classify all existing papers in database.

    Args:
        method: Classification method
        limit: Maximum papers to process (0 = all)
    """
    print("=" * 60)
    print("Classifying Existing Papers")
    print("=" * 60)

    # Load environment
    load_dotenv()

    # Initialize database
    db = get_database()

    # Get all papers
    cursor = db.conn.cursor()
    if limit > 0:
        cursor.execute("SELECT * FROM papers LIMIT ?", (limit,))
    else:
        cursor.execute("SELECT * FROM papers")

    papers = cursor.fetchall()

    if not papers:
        print("\n⚠ No papers found in database!")
        print("Run the system at least once to populate papers.")
        return False

    print(f"\nFound {len(papers)} papers to classify")
    print(f"Method: {method}")

    # Initialize LLM if needed
    llm = None
    if method in ["llm", "hybrid"]:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("\n⚠ Warning: ANTHROPIC_API_KEY not found!")
            print("Falling back to keyword-only classification")
            method = "keyword"
        else:
            llm = Anthropic(api_key=api_key)
            print("✓ LLM client initialized")

    # Initialize classifier
    classifier = DomainClassifier(llm=llm)

    # Check if domains exist
    domains = classifier.domains
    if not domains:
        print("\n❌ Error: No domains found in database!")
        print("Please run: python scripts/initialize_domains.py")
        return False

    print(f"✓ Loaded {len(domains)} domains")

    # Convert papers to PaperMetadata format
    paper_list = []
    for paper in papers:
        import json
        paper_dict = {
            "arxiv_id": paper["arxiv_id"],
            "title": paper["title"],
            "authors": json.loads(paper["authors"]),
            "abstract": paper["abstract"],
            "published": paper["published"],
            "categories": json.loads(paper["categories"]) if paper["categories"] else [],
            "url": paper["url"],
            "pdf_url": paper["pdf_url"]
        }
        paper_list.append(paper_dict)

    # Classify papers
    print(f"\nClassifying papers...")
    results = classifier.classify_batch(
        papers=paper_list,
        method=method,
        save_to_db=True
    )

    # Statistics
    total_classified = len([r for r in results.values() if r])
    total_classifications = sum(len(r) for r in results.values())

    print("\n" + "=" * 60)
    print("✅ Classification Complete!")
    print("=" * 60)
    print(f"\nStatistics:")
    print(f"  Papers processed: {len(papers)}")
    print(f"  Papers classified: {total_classified}")
    print(f"  Total classifications: {total_classifications}")
    print(f"  Avg classifications per paper: {total_classifications / len(papers):.2f}")

    # Display classification stats
    stats = classifier.get_classification_stats()
    print(f"\n  Classification method breakdown:")
    for method_name, count in stats["by_method"].items():
        print(f"    {method_name}: {count}")

    print(f"\n  Average confidence: {stats['average_confidence']:.3f}")

    print(f"\n  Top 10 domains:")
    for domain_name, count in stats["top_10_domains"]:
        print(f"    {domain_name}: {count} papers")

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Classify existing papers into domain taxonomy"
    )
    parser.add_argument(
        "--method",
        choices=["keyword", "llm", "hybrid"],
        default="hybrid",
        help="Classification method (default: hybrid)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum papers to classify (0 = all, default: 0)"
    )

    args = parser.parse_args()

    success = classify_existing_papers(
        method=args.method,
        limit=args.limit
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
