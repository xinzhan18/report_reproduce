"""
Initialize Domain Taxonomy

Creates predefined domain hierarchy for quantitative finance research.

Usage:
    python scripts/initialize_domains.py
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - sys, pathlib.Path, core.database, core.database_extensions
# OUTPUT: 对外提供 - initialize_domains函数, main函数(命令行入口), DOMAIN_HIERARCHY常量
# POSITION: 系统地位 - [Scripts/Initialization Layer] - 领域分类初始化脚本,创建量化金融研究的领域层级结构
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.database_extensions import DocumentMemoryExtensions


# Domain hierarchy definition
DOMAIN_HIERARCHY = {
    "Quantitative Finance": {
        "description": "Root domain for quantitative finance research",
        "keywords": ["quantitative", "finance", "trading", "portfolio", "risk"],
        "children": {
            "Trading Strategies": {
                "description": "Algorithmic trading strategies and systems",
                "keywords": ["trading", "strategy", "algorithm", "execution", "signal"],
                "children": {
                    "Momentum Strategies": {
                        "description": "Momentum and trend-following strategies",
                        "keywords": ["momentum", "trend", "following", "cross-sectional", "time-series"],
                        "children": {}
                    },
                    "Mean Reversion": {
                        "description": "Mean reversion and contrarian strategies",
                        "keywords": ["mean reversion", "contrarian", "oscillator", "reversal"],
                        "children": {}
                    },
                    "Pairs Trading": {
                        "description": "Pairs trading and statistical arbitrage",
                        "keywords": ["pairs trading", "cointegration", "spread", "arbitrage"],
                        "children": {}
                    },
                    "Statistical Arbitrage": {
                        "description": "Statistical arbitrage strategies",
                        "keywords": ["statistical arbitrage", "market neutral", "factor model"],
                        "children": {}
                    },
                    "High-Frequency Trading": {
                        "description": "High-frequency and microstructure trading",
                        "keywords": ["high-frequency", "HFT", "microstructure", "market making"],
                        "children": {}
                    }
                }
            },
            "Risk Management": {
                "description": "Risk measurement and management techniques",
                "keywords": ["risk", "var", "volatility", "drawdown", "hedging"],
                "children": {
                    "Market Risk": {
                        "description": "Market risk measurement and management",
                        "keywords": ["market risk", "var", "expected shortfall", "stress testing"],
                        "children": {}
                    },
                    "Credit Risk": {
                        "description": "Credit risk modeling and management",
                        "keywords": ["credit risk", "default", "spread", "rating"],
                        "children": {}
                    },
                    "Portfolio Risk": {
                        "description": "Portfolio-level risk management",
                        "keywords": ["portfolio risk", "correlation", "diversification"],
                        "children": {}
                    }
                }
            },
            "Portfolio Management": {
                "description": "Portfolio construction and optimization",
                "keywords": ["portfolio", "allocation", "optimization", "rebalancing"],
                "children": {
                    "Asset Allocation": {
                        "description": "Strategic and tactical asset allocation",
                        "keywords": ["asset allocation", "strategic", "tactical", "multi-asset"],
                        "children": {}
                    },
                    "Factor Investing": {
                        "description": "Factor-based investing strategies",
                        "keywords": ["factor", "value", "growth", "quality", "smart beta"],
                        "children": {}
                    },
                    "Multi-Asset Strategies": {
                        "description": "Cross-asset portfolio strategies",
                        "keywords": ["multi-asset", "cross-asset", "diversification"],
                        "children": {}
                    }
                }
            },
            "Derivatives and Options": {
                "description": "Derivatives pricing and strategies",
                "keywords": ["derivatives", "options", "futures", "swaps"],
                "children": {
                    "Options Pricing": {
                        "description": "Options pricing models and methods",
                        "keywords": ["options pricing", "black-scholes", "implied volatility"],
                        "children": {}
                    },
                    "Volatility Modeling": {
                        "description": "Volatility modeling and trading",
                        "keywords": ["volatility", "GARCH", "stochastic volatility", "VIX"],
                        "children": {}
                    },
                    "Hedging Strategies": {
                        "description": "Hedging and risk mitigation with derivatives",
                        "keywords": ["hedging", "delta", "gamma", "greek"],
                        "children": {}
                    }
                }
            },
            "Machine Learning in Finance": {
                "description": "Machine learning applications in finance",
                "keywords": ["machine learning", "deep learning", "neural network", "AI"],
                "children": {
                    "Prediction Models": {
                        "description": "ML models for price and return prediction",
                        "keywords": ["prediction", "forecasting", "regression", "classification"],
                        "children": {}
                    },
                    "Reinforcement Learning": {
                        "description": "RL for trading and portfolio management",
                        "keywords": ["reinforcement learning", "Q-learning", "policy gradient"],
                        "children": {}
                    }
                }
            }
        }
    }
}


def initialize_domains():
    """Initialize domain taxonomy in database."""
    print("=" * 60)
    print("Initializing Domain Taxonomy")
    print("=" * 60)

    db = get_database()

    # Add extension methods
    for method_name in dir(DocumentMemoryExtensions):
        if not method_name.startswith('_'):
            method = getattr(DocumentMemoryExtensions, method_name)
            if callable(method):
                bound_method = method.__get__(db, type(db))
                setattr(db, method_name, bound_method)

    # Check if already initialized
    existing_domains = db.get_all_domains()
    if existing_domains:
        print(f"\n⚠ Warning: {len(existing_domains)} domains already exist!")
        response = input("Do you want to re-initialize? (yes/no): ")
        if response.lower() != 'yes':
            print("Initialization cancelled.")
            return False

        # Clear existing domains
        print("Clearing existing domains...")
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM paper_domains")
        cursor.execute("DELETE FROM domains")
        db.conn.commit()

    # Insert domains recursively
    domain_count = insert_domain_recursive(db, DOMAIN_HIERARCHY, parent_id=None)

    print("\n" + "=" * 60)
    print(f"✅ Initialized {domain_count} domains successfully!")
    print("=" * 60)

    # Display hierarchy
    print("\nDomain Hierarchy:")
    display_hierarchy(db)

    print("\nNext step:")
    print("  Run: python scripts/classify_existing_papers.py")

    return True


def insert_domain_recursive(db, hierarchy: dict, parent_id: int = None, level: int = 0) -> int:
    """
    Insert domains recursively.

    Args:
        db: Database instance
        hierarchy: Domain hierarchy dict
        parent_id: Parent domain ID
        level: Current level (for logging)

    Returns:
        Number of domains inserted
    """
    count = 0

    for domain_name, domain_data in hierarchy.items():
        description = domain_data.get("description", "")
        keywords = domain_data.get("keywords", [])
        children = domain_data.get("children", {})

        # Insert domain
        domain_id = db.add_domain(
            name=domain_name,
            parent_id=parent_id,
            description=description,
            keywords=keywords
        )

        indent = "  " * level
        print(f"{indent}✓ {domain_name} (ID: {domain_id})")

        count += 1

        # Insert children
        if children:
            count += insert_domain_recursive(db, children, parent_id=domain_id, level=level + 1)

    return count


def display_hierarchy(db, parent_id: int = None, level: int = 0):
    """Display domain hierarchy."""
    if parent_id is None:
        domains = db.get_root_domains()
    else:
        domains = db.get_child_domains(parent_id)

    indent = "  " * level
    for domain in domains:
        print(f"{indent}- {domain['name']} (papers: {domain['paper_count']})")
        display_hierarchy(db, parent_id=domain['id'], level=level + 1)


if __name__ == "__main__":
    success = initialize_domains()
    if not success:
        sys.exit(1)
