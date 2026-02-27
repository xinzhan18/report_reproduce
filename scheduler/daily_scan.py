"""
Daily paper scanning scheduler for automated research discovery.

Scans arXiv daily for new papers in quantitative finance and related fields,
and triggers research pipelines for promising topics.
"""

import schedule
import time
from datetime import datetime
from typing import List, Dict, Any
from tools.paper_fetcher import PaperFetcher
from scheduler.pipeline_runner import PipelineRunner
from config.agent_config import get_agent_config
import logging


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyScanner:
    """
    Manages daily scanning of papers and automatic research initiation.
    """

    def __init__(self):
        """Initialize daily scanner."""
        self.paper_fetcher = PaperFetcher()
        self.pipeline_runner = PipelineRunner()
        self.config = get_agent_config("ideation")

    def scan_and_analyze(self) -> Dict[str, Any]:
        """
        Perform daily scan of papers.

        Returns:
            Dictionary with scan results
        """
        logger.info("="*60)
        logger.info("DAILY PAPER SCAN - Starting")
        logger.info(f"Time: {datetime.now().isoformat()}")
        logger.info("="*60)

        # Get configuration
        categories = self.config.get("focus_categories", [])
        keywords = self.config.get("keywords", [])
        min_papers_for_trigger = self.config.get("min_papers_for_trigger", 5)

        # Fetch recent papers (last 24 hours)
        logger.info(f"Scanning categories: {', '.join(categories)}")

        papers = self.paper_fetcher.fetch_recent_papers(
            categories=categories,
            days_back=1,  # Last 24 hours
            max_results=100
        )

        logger.info(f"Found {len(papers)} new papers")

        if len(papers) == 0:
            logger.info("No new papers found. Scan complete.")
            return {
                "scan_time": datetime.now().isoformat(),
                "papers_found": 0,
                "pipelines_triggered": 0
            }

        # Filter by relevance to keywords
        relevant_papers = self.paper_fetcher.filter_papers_by_relevance(
            papers,
            keywords=keywords,
            min_score=0.3
        )

        logger.info(f"Found {len(relevant_papers)} relevant papers")

        # Analyze papers for research opportunities
        opportunities = self.identify_research_opportunities(relevant_papers)

        logger.info(f"Identified {len(opportunities)} research opportunities")

        # Trigger pipelines for promising opportunities
        pipelines_triggered = 0

        if len(relevant_papers) >= min_papers_for_trigger:
            for opportunity in opportunities[:3]:  # Limit to top 3
                try:
                    logger.info(f"Triggering pipeline for: {opportunity['direction']}")

                    # Start research pipeline in background
                    self.pipeline_runner.run_project(
                        research_direction=opportunity["direction"],
                        background=False  # Set to True for async execution
                    )

                    pipelines_triggered += 1

                except Exception as e:
                    logger.error(f"Error triggering pipeline: {e}")

        logger.info("="*60)
        logger.info(f"DAILY PAPER SCAN - Complete")
        logger.info(f"Pipelines triggered: {pipelines_triggered}")
        logger.info("="*60)

        return {
            "scan_time": datetime.now().isoformat(),
            "papers_found": len(papers),
            "relevant_papers": len(relevant_papers),
            "opportunities_identified": len(opportunities),
            "pipelines_triggered": pipelines_triggered
        }

    def identify_research_opportunities(
        self,
        papers: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Identify research opportunities from papers.

        Args:
            papers: List of paper metadata

        Returns:
            List of research opportunity descriptions
        """
        # Group papers by theme
        themes = self._extract_themes(papers)

        # Create research opportunities
        opportunities = []

        for theme, theme_papers in themes.items():
            if len(theme_papers) >= 2:  # At least 2 papers on same theme
                opportunities.append({
                    "direction": theme,
                    "paper_count": len(theme_papers),
                    "papers": theme_papers
                })

        # Sort by paper count (descending)
        opportunities.sort(key=lambda x: x["paper_count"], reverse=True)

        return opportunities

    def _extract_themes(
        self,
        papers: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract common themes from papers.

        Args:
            papers: List of papers

        Returns:
            Dictionary mapping themes to papers
        """
        themes: Dict[str, List[Dict[str, Any]]] = {}

        # Define theme keywords
        theme_keywords = {
            "momentum strategies": ["momentum", "trend following", "moving average"],
            "mean reversion": ["mean reversion", "pairs trading", "cointegration"],
            "risk management": ["risk", "drawdown", "var", "volatility"],
            "portfolio optimization": ["portfolio", "optimization", "allocation"],
            "market microstructure": ["microstructure", "liquidity", "high-frequency"],
            "factor models": ["factor", "fama french", "multifactor"],
            "machine learning": ["machine learning", "neural network", "deep learning"],
        }

        for paper in papers:
            text = f"{paper['title']} {paper['abstract']}".lower()

            for theme, keywords in theme_keywords.items():
                if any(kw in text for kw in keywords):
                    if theme not in themes:
                        themes[theme] = []
                    themes[theme].append(paper)

        return themes

    def run_once(self):
        """Run scan once (for testing)."""
        return self.scan_and_analyze()

    def run_scheduler(self, scan_time: str = "08:00"):
        """
        Run scheduler continuously.

        Args:
            scan_time: Time to run daily scan (HH:MM format)
        """
        logger.info(f"Starting daily scanner. Scheduled for {scan_time} daily.")

        # Schedule daily scan
        schedule.every().day.at(scan_time).do(self.scan_and_analyze)

        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")

    def run_interval(self, hours: int = 24):
        """
        Run scanner at regular intervals.

        Args:
            hours: Interval in hours
        """
        logger.info(f"Starting scanner with {hours}-hour interval")

        schedule.every(hours).hours.do(self.scan_and_analyze)

        try:
            while True:
                schedule.run_pending()
                time.sleep(300)  # Check every 5 minutes

        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")


def main():
    """
    Main entry point for daily scanner.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Daily paper scanner")
    parser.add_argument(
        "--mode",
        choices=["once", "daily", "interval"],
        default="once",
        help="Scan mode: once (run once), daily (schedule daily), interval (run every N hours)"
    )
    parser.add_argument(
        "--time",
        default="08:00",
        help="Time for daily scan (HH:MM format)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=24,
        help="Interval in hours for interval mode"
    )

    args = parser.parse_args()

    scanner = DailyScanner()

    if args.mode == "once":
        logger.info("Running single scan...")
        result = scanner.run_once()
        logger.info(f"Scan complete: {result}")

    elif args.mode == "daily":
        logger.info(f"Starting daily scheduler (scan at {args.time})")
        scanner.run_scheduler(scan_time=args.time)

    elif args.mode == "interval":
        logger.info(f"Starting interval scheduler ({args.interval} hours)")
        scanner.run_interval(hours=args.interval)


if __name__ == "__main__":
    main()
