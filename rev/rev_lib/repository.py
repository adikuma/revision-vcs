import os
import hashlib
import zlib
import time

# repository constants
repo_dir = ".rev"
objects_dir = os.path.join(repo_dir, "objects")
refs_dir = os.path.join(repo_dir, "refs")
heads_dir = os.path.join(refs_dir, "heads")
head_file = os.path.join(repo_dir, "head")
main_branch_file = os.path.join(heads_dir, "main")
index_file = os.path.join(repo_dir, "index")

def init_repository():
    """initialize a new rev repository"""
    if os.path.exists(repo_dir):
        print(f"error: rev repository already exists in {os.path.abspath(repo_dir)}")
        return False

    try:
        # create directory structure
        os.makedirs(objects_dir)
        os.makedirs(refs_dir)
        os.makedirs(heads_dir)
        
        # create head file pointing to main branch
        with open(head_file, "w") as f:
            f.write("ref: refs/heads/main")
        
        # create main branch reference (empty for now)
        with open(main_branch_file, "w"):
            pass
        
        # create empty index file
        with open(index_file, "w"):
            pass

        return True
    except OSError as e:
        print(f"error: failed to initialize repository - {e.strerror}")
        return False

def read_file(file_path):
    try:
        with open(file_path, "rb") as file:
            return file.read()
    except FileNotFoundError:
        return None

def create_blob(file_path):
    content = read_file(file_path)
    if content is None:
        return None
    
    header = f"blob {len(content)}\0".encode()
    combined_data = header + content
    sha1_hash = hashlib.sha1(combined_data)
    hex_digest = sha1_hash.hexdigest()
    
    compressed_data = zlib.compress(combined_data)
    
    # store in proper object path
    obj_dir = os.path.join(objects_dir, hex_digest[:2])
    os.makedirs(obj_dir, exist_ok=True)
    obj_path = os.path.join(obj_dir, hex_digest[2:])
    
    with open(obj_path, "wb") as f:
        f.write(compressed_data)
        
    return hex_digest

def update_index(file_path, blob_hash):
    # get relative path and normalize
    rel_path = os.path.relpath(file_path).replace("\\", "/")
    
    # get simplified mode
    mode = "100755" if os.access(file_path, os.X_OK) else "100644"
    timestamp = os.path.getmtime(file_path)
    
    # read existing index
    entries = []
    if os.path.exists(index_file):
        with open(index_file, "r") as f:
            entries = f.readlines()
    
    # update or add entry
    new_entry = f"{mode} {blob_hash} {timestamp} {rel_path}\n"
    new_entries = []
    found = False
    
    for entry in entries:
        # extract path from entry
        entry_path = entry.strip().split()[-1]
        if entry_path == rel_path:
            new_entries.append(new_entry)
            found = True
        else:
            new_entries.append(entry)
    
    if not found:
        new_entries.append(new_entry)
    
    # write back to index
    with open(index_file, "w") as f:
        f.writelines(new_entries)

def read_index():
    """read index file and return dictionary"""
    index = {}
    if not os.path.exists(index_file):
        return index
        
    with open(index_file, "r") as f:
        for line in f:
            parts = line.strip().split(maxsplit=3)
            if len(parts) < 4:
                continue
            mode, blob_hash, timestamp, path = parts
            index[path] = {
                "mode": mode,
                "blob_hash": blob_hash,
                "timestamp": float(timestamp)
            }
    return index

def create_tree(index_entries):
    """create tree object from index entries"""
    content = b""
    for path, data in index_entries.items():
        # use base name for tree entry
        basename = os.path.basename(path)
        bin_sha = bytes.fromhex(data["blob_hash"])
        entry = f"{data['mode']} {basename}\0".encode() + bin_sha
        content += entry

    header = f"tree {len(content)}\0".encode()
    full_data = header + content
    sha = hashlib.sha1(full_data).hexdigest()
    
    # store tree object
    obj_dir = os.path.join(objects_dir, sha[:2])
    os.makedirs(obj_dir, exist_ok=True)
    obj_path = os.path.join(obj_dir, sha[2:])
    
    with open(obj_path, "wb") as f:
        f.write(zlib.compress(full_data))
    
    return sha

def create_commit(tree_hash, parent_hash, message, author):
    """create commit object"""
    # build commit content
    lines = [
        f"tree {tree_hash}",
        f"parent {parent_hash}" if parent_hash else "",
        f"author {author} {int(time.time())}",
        f"committer {author} {int(time.time())}",
        "",
        message
    ]
    content = "\n".join(filter(None, lines)).encode()
    
    header = f"commit {len(content)}\0".encode()
    full_data = header + content
    sha = hashlib.sha1(full_data).hexdigest()
    
    # store commit object
    obj_dir = os.path.join(objects_dir, sha[:2])
    os.makedirs(obj_dir, exist_ok=True)
    obj_path = os.path.join(obj_dir, sha[2:])
    
    with open(obj_path, "wb") as f:
        f.write(zlib.compress(full_data))
    
    return sha

def get_head_commit():
    """get current head commit hash"""
    # read head reference
    if not os.path.exists(head_file):
        return None
        
    with open(head_file, "r") as f:
        head_ref = f.read().strip()
    
    if head_ref.startswith("ref: "):
        ref_path = head_ref[5:]
        branch_file = os.path.join(repo_dir, ref_path)
        if os.path.exists(branch_file):
            with open(branch_file, "r") as f:
                return f.read().strip()
    return None

def update_head_ref(commit_hash):
    """update head reference to new commit"""
    if not os.path.exists(head_file):
        return False
        
    with open(head_file, "r") as f:
        head_ref = f.read().strip()
    
    if head_ref.startswith("ref: "):
        ref_path = head_ref[5:]
        branch_file = os.path.join(repo_dir, ref_path)
        with open(branch_file, "w") as f:
            f.write(commit_hash)
        return True
    return False

def commit_changes(message, author="user <user@example.com>"):
    """commit staged changes"""
    # get current index
    index_entries = read_index()
    if not index_entries:
        print("nothing to commit")
        return None
    # create tree from index
    tree_hash = create_tree(index_entries)
    # get parent commit
    parent_hash = get_head_commit()
    # create commit object
    commit_hash = create_commit(tree_hash, parent_hash, message, author)
    # update head reference
    update_head_ref(commit_hash)
    # clear staging area (optional)
    with open(index_file, "w"):
        pass
    
    return commit_hash