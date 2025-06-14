#!/usr/bin/env python3
import argparse
import sys
import os
import time
from rev.rev_lib.repository import (
    init_repository,
    create_blob,
    update_index,
    commit_changes,
    get_head_commit,
    revert_to_commit,
    get_status,
    get_commit_history,
    read_object,
)


def main():
    parser = argparse.ArgumentParser(
        prog="rev", description="rev - version control system"
    )
    subparsers = parser.add_subparsers(dest="command", title="commands")

    # init command
    init_parser = subparsers.add_parser("init", help="initialize a new repository")

    # add command
    add_parser = subparsers.add_parser("add", help="stage files for commit")
    add_parser.add_argument("files", nargs="+", help="files to add")

    # commit command
    commit_parser = subparsers.add_parser("commit", help="commit staged changes")
    commit_parser.add_argument(
        "-m", "--message", required=True, help="commit message"
    )

    # log command
    log_parser = subparsers.add_parser("log", help="show commit history")

    # status command
    status_parser = subparsers.add_parser(
        "status", help="show working directory status"
    )

    # revert command
    revert_parser = subparsers.add_parser(
        "revert", help="revert to a previous commit"
    )
    revert_parser.add_argument("commit_hash", help="commit hash to revert to")

    # parse arguments
    args = parser.parse_args()

    if args.command == "init":
        try:
            if init_repository():
                print(
                    f"initialized empty rev repository in {os.path.abspath('.rev')}"
                )
        except OSError as e:
            print(f"error: {e.strerror}")
            sys.exit(1)

    elif args.command == "add":
        # check if repository exists
        if not os.path.exists(".rev"):
            print("error: not a rev repository")
            sys.exit(1)

        for file_path in args.files:
            if not os.path.exists(file_path):
                print(f"error: {file_path} does not exist")
                continue
            if os.path.isdir(file_path):
                print(f"error: {file_path} is a directory")
                continue

            blob_hash = create_blob(file_path)
            if blob_hash:
                update_index(file_path, blob_hash)
                print(f"added {file_path}")
            else:
                print(f"error: failed to add {file_path}")

    elif args.command == "commit":
        # check if repository exists
        if not os.path.exists(".rev"):
            print("error: not a rev repository")
            sys.exit(1)

        commit_hash = commit_changes(args.message)
        if commit_hash:
            print(f"committed: {commit_hash[:7]} {args.message}")

    elif args.command == "log":
        # check if repository exists
        if not os.path.exists(".rev"):
            print("error: not a rev repository")
            sys.exit(1)

        history = get_commit_history()
        if not history:
            print("no commits yet")
            return

        for commit_hash in history:
            obj_type, content = read_object(commit_hash)
            if obj_type != "commit":
                continue

            lines = content.decode().splitlines()
            message = ""
            author = ""
            date = ""

            # parse commit content
            in_message = False
            for line in lines:
                if line.startswith("author "):
                    parts = line.split()
                    timestamp = int(parts[-1])
                    author = " ".join(parts[1:-1])
                    date = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(timestamp)
                    )
                elif line == "":
                    in_message = True
                elif in_message and line:
                    message = line
                    break

            print(f"commit {commit_hash}")
            print(f"author: {author}")
            print(f"date:   {date}")
            print(f"    {message}\n")

    elif args.command == "status":
        # check if repository exists
        if not os.path.exists(".rev"):
            print("error: not a rev repository")
            sys.exit(1)

        status_info = get_status()
        if (
            not status_info["modified"]
            and not status_info["untracked"]
            and not status_info["deleted"]
        ):
            print("nothing to commit, working directory clean")
        else:
            if status_info["modified"]:
                print("changes not staged for commit:")
                for file in status_info["modified"]:
                    print(f"\tmodified:   {file}")
            if status_info["deleted"]:
                print("deleted files:")
                for file in status_info["deleted"]:
                    print(f"\tdeleted:    {file}")
            if status_info["untracked"]:
                print("untracked files:")
                for file in status_info["untracked"]:
                    print(f"\t{file}")

    elif args.command == "revert":
        # check if repository exists
        if not os.path.exists(".rev"):
            print("error: not a rev repository")
            sys.exit(1)

        if revert_to_commit(args.commit_hash):
            print(f"reverted to commit {args.commit_hash[:7]}")
        else:
            print("error: revert failed")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()