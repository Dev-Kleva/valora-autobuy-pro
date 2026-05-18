#!/usr/bin/env python3
"""
Rename autobuy-agent folder to valora
Run this script from the autobuy-agent directory
"""

import os
import shutil

def rename_to_valora():
    """Rename the current directory to valora"""

    current_dir = os.getcwd()
    current_name = os.path.basename(current_dir)
    parent_dir = os.path.dirname(current_dir)

    print(f"Current directory: {current_name}")
    print(f"Full path: {current_dir}")

    if current_name != "autobuy-agent":
        print(f"❌ Error: Not in autobuy-agent directory (currently in: {current_name})")
        return False

    new_name = "valora"
    new_path = os.path.join(parent_dir, new_name)

    print(f"\nWill rename to: {new_name}")
    print(f"New path: {new_path}")

    # Check if destination exists
    if os.path.exists(new_path):
        print(f"❌ Error: {new_path} already exists!")
        return False

    # Confirm
    try:
        confirm = input(f"\nRename '{current_name}' to '{new_name}'? (y/N): ").lower().strip()
    except KeyboardInterrupt:
        print("\n❌ Cancelled")
        return False

    if confirm not in ['y', 'yes']:
        print("❌ Cancelled")
        return False

    # Rename
    try:
        print("🔄 Renaming...")
        os.rename(current_dir, new_path)
        print("✅ Successfully renamed to 'valora'!")
        print(f"\n📁 New location: {new_path}")
        print("\n📋 Next steps:")
        print("1. Close VS Code")
        print("2. Reopen VS Code")
        print(f"3. File → Open Folder → {new_path}")
        print("4. Test: python test_amazon_search.py")
        return True

    except Exception as e:
        print(f"❌ Rename failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Valora Project Rename Tool")
    print("=" * 40)
    rename_to_valora()