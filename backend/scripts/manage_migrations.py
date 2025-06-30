#!/usr/bin/env python3
"""
Migration Management Script

Provides a convenient interface for common Alembic migration operations:
- Creating new migrations
- Applying migrations
- Rolling back migrations
- Checking migration status
- Validating migration integrity
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from typing import List, Optional


def run_command(command: List[str], description: str) -> bool:
    """Run a command and handle output."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, check=True, text=True)
        print("✅ Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {e}")
        return False


def create_migration(message: str, autogenerate: bool = True) -> None:
    """Create a new migration."""
    command = ["alembic", "revision"]
    if autogenerate:
        command.append("--autogenerate")
    command.extend(["-m", message])
    
    description = f"Creating {'auto-generated' if autogenerate else 'empty'} migration: {message}"
    run_command(command, description)


def apply_migrations(target: Optional[str] = None) -> None:
    """Apply migrations up to a target (or head if not specified)."""
    target = target or "head"
    command = ["alembic", "upgrade", target]
    description = f"Applying migrations to {target}"
    run_command(command, description)


def rollback_migrations(target: str) -> None:
    """Rollback migrations to a target."""
    command = ["alembic", "downgrade", target]
    description = f"Rolling back migrations to {target}"
    run_command(command, description)


def show_status() -> None:
    """Show current migration status."""
    print("🔧 Migration Status:")
    print("\n📍 Current revision:")
    subprocess.run(["alembic", "current"], check=False)
    
    print("\n📜 Migration history:")
    subprocess.run(["alembic", "history", "--verbose"], check=False)
    
    print("\n🔍 Pending migrations:")
    # Check if there are any pending migrations
    try:
        result = subprocess.run(
            ["alembic", "check"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        print("✅ Database is up to date")
    except subprocess.CalledProcessError:
        print("⚠️  Database is not up to date - migrations pending")


def validate_migrations() -> None:
    """Validate migration integrity."""
    print("🔧 Validating migration integrity...")
    
    # Check that all migration files exist
    versions_dir = Path("alembic/versions")
    if not versions_dir.exists():
        print("❌ Alembic versions directory not found")
        return
    
    migration_files = list(versions_dir.glob("*.py"))
    if not migration_files:
        print("⚠️  No migration files found")
        return
    
    print(f"✅ Found {len(migration_files)} migration files")
    
    # Test that migrations can be applied and rolled back
    print("\n🔧 Testing migration rollback/upgrade cycle...")
    
    commands = [
        (["alembic", "downgrade", "base"], "Rollback to base"),
        (["alembic", "upgrade", "head"], "Upgrade to head"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return
    
    print("✅ Migration integrity validated")


def reset_database() -> None:
    """Reset the database by rolling back all migrations."""
    print("⚠️  This will remove all data from the database!")
    confirm = input("Are you sure you want to reset the database? (y/N): ")
    
    if confirm.lower() == 'y':
        run_command(["alembic", "downgrade", "base"], "Resetting database")
        print("✅ Database reset complete")
    else:
        print("❌ Database reset cancelled")


def main() -> None:
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Migration Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status                           # Show migration status
  %(prog)s create "Add user table"          # Create new auto-migration
  %(prog)s create "Custom changes" --empty  # Create empty migration
  %(prog)s apply                            # Apply all pending migrations
  %(prog)s apply 12345                      # Apply up to specific revision
  %(prog)s rollback 12345                   # Rollback to specific revision
  %(prog)s rollback base                    # Rollback all migrations
  %(prog)s validate                         # Validate migration integrity
  %(prog)s reset                            # Reset database (remove all data)
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Status command
    subparsers.add_parser("status", help="Show migration status")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("message", help="Migration message")
    create_parser.add_argument("--empty", action="store_true", help="Create empty migration (no autogenerate)")
    
    # Apply command
    apply_parser = subparsers.add_parser("apply", help="Apply migrations")
    apply_parser.add_argument("target", nargs="?", help="Target revision (default: head)")
    
    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback migrations")
    rollback_parser.add_argument("target", help="Target revision")
    
    # Validate command
    subparsers.add_parser("validate", help="Validate migration integrity")
    
    # Reset command
    subparsers.add_parser("reset", help="Reset database (remove all data)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Ensure we're in the right directory
    if not Path("alembic.ini").exists():
        print("❌ Error: alembic.ini not found. Run this script from the project root directory.")
        sys.exit(1)
    
    # Execute the requested command
    if args.command == "status":
        show_status()
    elif args.command == "create":
        create_migration(args.message, not args.empty)
    elif args.command == "apply":
        apply_migrations(args.target)
    elif args.command == "rollback":
        rollback_migrations(args.target)
    elif args.command == "validate":
        validate_migrations()
    elif args.command == "reset":
        reset_database()


if __name__ == "__main__":
    main()