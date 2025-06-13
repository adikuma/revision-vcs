#!/usr/bin/env python3
import argparse
import sys
import os
from .rev_lib.repository import (
    init_repository, 
    create_blob, 
    update_index,
    commit_changes,
    get_head_commit
)

def main():
    parser = argparse.ArgumentParser(prog="rev", description="rev - version control system")
    subparsers = parser.add_subparsers(dest="command", title="commands")
    
    # init command
    init_parser = subparsers.add_parser("init", help="initialize a new repository")
    
    # add command
    add_parser = subparsers.add_parser("add", help="stage files for commit")
    add_parser.add_argument("files", nargs="+", help="files to add")
    
    # commit command
    commit_parser = subparsers.add_parser("commit", help="commit staged changes")
    commit_parser.add_argument("-m", "--message", required=True, help="commit message")
    
    # log command (simple)
    log_parser = subparsers.add_parser("log", help="show commit history")
    
    # parse arguments
    args = parser.parse_args()
    
    if args.command == "init":
        try:
            if init_repository():
                print(f"initialized empty rev repository in {os.path.abspath('.rev')}")
        except OSError as e:
            print(f"error: {e.strerror}")
            sys.exit(1)
            
    elif args.command == "add":
        for file_path in args.files:
            if not os.path.exists(file_path):
                print(f"error: {file_path} does not exist")
                continue
            blob_hash = create_blob(file_path)
            if blob_hash:
                update_index(file_path, blob_hash)
                print(f"added {file_path}")
            else:
                print(f"error: failed to add {file_path}")
                
    elif args.command == "commit":
        commit_hash = commit_changes(args.message)
        if commit_hash:
            print(f"committed: {commit_hash[:7]} {args.message}")
            
    elif args.command == "log":
        commit_hash = get_head_commit()
        if commit_hash:
            print(f"commit {commit_hash[:7]} (head)")
        else:
            print("no commits yet")
            
    else:
        parser.print_help()
        sys.exit(1)
        
if __name__ == "__main__":
    main()