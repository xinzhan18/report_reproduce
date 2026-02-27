"""
Database Migration v2 - Add Document Memory System Tables

Adds three new tables to support the document memory system:
1. domains - Hierarchical domain taxonomy
2. paper_domains - Paper-to-domain mappings with relevance scores
3. paper_analysis_cache - Cached analysis results from deep literature analysis

Usage:
    python scripts/migrate_database_v2.py
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - sqlite3, pathlib.Path, sys
# OUTPUT: 对外提供 - migrate_database函数, main函数(命令行入口)
# POSITION: 系统地位 - [Scripts/Migration Layer] - 数据库迁移脚本,升级database schema到v2版本(添加文档记忆系统表)
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import sqlite3
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def migrate_database(db_path: Path = None):
    """
    Run database migration to add document memory tables.

    Args:
        db_path: Path to database file (default: data/research.db)
    """
    if db_path is None:
        db_path = Path("data/research.db")

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        print("Please run the system at least once to create the initial database.")
        return False

    print(f"Migrating database at: {db_path}")
    print("=" * 60)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Check if migration already applied
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='domains'
        """)
        if cursor.fetchone():
            print("⚠ Migration already applied! Tables exist.")
            response = input("Do you want to re-run the migration? (yes/no): ")
            if response.lower() != 'yes':
                print("Migration cancelled.")
                return False
            print("Dropping existing tables...")
            cursor.execute("DROP TABLE IF EXISTS paper_domains")
            cursor.execute("DROP TABLE IF EXISTS domains")
            cursor.execute("DROP TABLE IF EXISTS paper_analysis_cache")
            conn.commit()

        # ===== Create domains table =====
        print("\n1. Creating 'domains' table...")
        cursor.execute("""
            CREATE TABLE domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                parent_id INTEGER,
                description TEXT,
                keywords TEXT,  -- JSON array of keywords
                paper_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES domains(id)
            )
        """)
        print("✓ Created 'domains' table")

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_domains_name ON domains(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_domains_parent ON domains(parent_id)")
        print("✓ Created indexes for 'domains'")

        # ===== Create paper_domains table =====
        print("\n2. Creating 'paper_domains' table...")
        cursor.execute("""
            CREATE TABLE paper_domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id TEXT NOT NULL,  -- arxiv_id from papers table
                domain_id INTEGER NOT NULL,
                relevance_score REAL DEFAULT 1.0,  -- 0.0 to 1.0
                auto_classified BOOLEAN DEFAULT TRUE,
                classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                classified_by TEXT,  -- 'keyword', 'llm', 'manual'
                FOREIGN KEY (domain_id) REFERENCES domains(id),
                UNIQUE(paper_id, domain_id)
            )
        """)
        print("✓ Created 'paper_domains' table")

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_domains_paper ON paper_domains(paper_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_domains_domain ON paper_domains(domain_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_domains_score ON paper_domains(relevance_score)")
        print("✓ Created indexes for 'paper_domains'")

        # ===== Create paper_analysis_cache table =====
        print("\n3. Creating 'paper_analysis_cache' table...")
        cursor.execute("""
            CREATE TABLE paper_analysis_cache (
                arxiv_id TEXT PRIMARY KEY,
                full_text_length INTEGER,
                sections_extracted TEXT,  -- JSON: {intro, methods, results, conclusion, ...}
                structured_insights TEXT,  -- JSON: StructuredInsights dataclass
                deep_insights TEXT,  -- JSON: DeepInsights dataclass (if analyzed deeply)
                analysis_version TEXT DEFAULT 'v1.0',
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (arxiv_id) REFERENCES papers(arxiv_id)
            )
        """)
        print("✓ Created 'paper_analysis_cache' table")

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_cache_version ON paper_analysis_cache(analysis_version)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_cache_analyzed ON paper_analysis_cache(analyzed_at)")
        print("✓ Created indexes for 'paper_analysis_cache'")

        # Commit all changes
        conn.commit()
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("\nNew tables created:")
        print("  - domains: Domain taxonomy for organizing papers")
        print("  - paper_domains: Paper-to-domain mappings")
        print("  - paper_analysis_cache: Cached analysis results")
        print("\nNext steps:")
        print("  1. Run: python scripts/initialize_domains.py")
        print("  2. Run: python scripts/classify_existing_papers.py")

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def verify_migration(db_path: Path = None):
    """
    Verify that migration was successful.

    Args:
        db_path: Path to database file
    """
    if db_path is None:
        db_path = Path("data/research.db")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print("Verifying migration...")
    print("=" * 60)

    tables_to_check = ['domains', 'paper_domains', 'paper_analysis_cache']
    all_exist = True

    for table_name in tables_to_check:
        cursor.execute(f"""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name=?
        """, (table_name,))
        if cursor.fetchone():
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"✓ {table_name}: exists ({count} rows)")
        else:
            print(f"❌ {table_name}: NOT FOUND")
            all_exist = False

    conn.close()

    if all_exist:
        print("\n✅ All tables verified successfully!")
    else:
        print("\n⚠ Some tables are missing!")

    return all_exist


if __name__ == "__main__":
    print("Database Migration v2: Document Memory System")
    print("=" * 60)

    # Run migration
    success = migrate_database()

    if success:
        # Verify
        verify_migration()
    else:
        print("\nMigration was not completed.")
        sys.exit(1)
