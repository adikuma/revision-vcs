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
    """read file content as bytes"""
    try:
        with open(file_path, "rb") as file:
            return file.read()
    except FileNotFoundError:
        return None

def create_blob(file_path):
    """create blob object from file content"""
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
    """update staging area with file info"""
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
    return commit_hash

def read_object(sha):
    """read an object by sha-1 hash and return (obj_type, content)"""
    obj_path = os.path.join(objects_dir, sha[:2], sha[2:])
    if not os.path.exists(obj_path):
        return None, None
        
    with open(obj_path, 'rb') as f:
        compressed = f.read()
    
    raw = zlib.decompress(compressed)
    null_idx = raw.find(b'\0')
    header = raw[:null_idx].decode()
    content = raw[null_idx+1:]
    
    obj_type, size = header.split()
    return obj_type, content

def get_commit_tree(commit_hash):
    """get the tree hash from a commit object"""
    obj_type, commit_data = read_object(commit_hash)
    if obj_type != 'commit':
        return None
        
    lines = commit_data.decode().splitlines()
    for line in lines:
        if line.startswith('tree '):
            return line.split()[1]
    return None

def restore_tree(tree_hash, base_path=''):
    """restore files from a tree object recursively"""
    obj_type, tree_data = read_object(tree_hash)
    if obj_type != 'tree':
        return
        
    # parse tree entries: [mode] [name]\0[20-byte hash]
    pos = 0
    while pos < len(tree_data):
        # find null terminator after filename
        null_idx = tree_data.find(b'\0', pos)
        if null_idx == -1:
            break
            
        # parse mode and filename
        header = tree_data[pos:null_idx].decode()
        mode, name = header.split(maxsplit=1)
        # get 20-byte binary hash
        bin_hash = tree_data[null_idx+1:null_idx+21]
        hex_hash = bin_hash.hex()
        pos = null_idx + 21
        
        full_path = os.path.join(base_path, name)
        
        if mode == '40000':  # directory
            os.makedirs(full_path, exist_ok=True)
            restore_tree(hex_hash, full_path)
        else:  # file
            obj_type, content = read_object(hex_hash)
            if obj_type == 'blob':
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'wb') as f:
                    f.write(content)

def revert_to_commit(commit_hash):
    """revert working directory to a specific commit"""
    tree_hash = get_commit_tree(commit_hash)
    if not tree_hash:
        print(f"error: commit {commit_hash} has no tree")
        return False
        
    # restore files from the tree
    restore_tree(tree_hash)
    
    # update index to match the commit
    index_entries = {}
    def collect_entries(tree_hash, base_path=''):
        obj_type, tree_data = read_object(tree_hash)
        if obj_type != 'tree':
            return
            
        pos = 0
        while pos < len(tree_data):
            null_idx = tree_data.find(b'\0', pos)
            if null_idx == -1:
                break
                
            header = tree_data[pos:null_idx].decode()
            mode, name = header.split(maxsplit=1)
            bin_hash = tree_data[null_idx+1:null_idx+21]
            hex_hash = bin_hash.hex()
            pos = null_idx + 21
            
            full_path = os.path.join(base_path, name).replace('\\', '/')
            
            if mode == '40000':  # directory
                collect_entries(hex_hash, full_path)
            else:  # file
                index_entries[full_path] = {
                    'mode': mode,
                    'blob_hash': hex_hash,
                    'timestamp': os.path.getmtime(full_path) if os.path.exists(full_path) else time.time()
                }
    
    collect_entries(tree_hash)
    with open(index_file, 'w') as f:
        for path, data in index_entries.items():
            f.write(f"{data['mode']} {data['blob_hash']} {int(data['timestamp'])} {path}\n")
    
    with open(head_file, 'w') as f:
        f.write(commit_hash)
    return True

def compute_file_hash(file_path):
    """compute file hash without storing as blob"""
    content = read_file(file_path)
    if content is None:
        return None
    header = f"blob {len(content)}\0".encode()
    combined_data = header + content
    return hashlib.sha1(combined_data).hexdigest()

def get_working_directory_files():
    """get all files in working directory except .rev"""
    wd_files = set()
    for dirpath, _, filenames in os.walk('.'):
        # skip .rev directory
        if repo_dir in dirpath.split(os.sep):
            continue
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path).replace('\\', '/')
            wd_files.add(rel_path)
    return wd_files

def get_status():
    """get repository status: modified and untracked files"""
    index_entries = read_index()
    wd_files = get_working_directory_files()
    
    modified = []
    untracked = list(wd_files - set(index_entries.keys()))
    
    # check modified files
    for path, entry in index_entries.items():
        if path in wd_files:
            current_hash = compute_file_hash(path)
            if current_hash != entry['blob_hash']:
                modified.append(path)
    
    return {
        'modified': modified,
        'untracked': untracked
    }

def get_commit_history():
    """get full commit history starting from head"""
    history = []
    current = get_head_commit()
    while current:
        history.append(current)
        # get parent commit
        obj_type, content = read_object(current)
        if obj_type != 'commit':
            break
        lines = content.decode().splitlines()
        parent = None
        for line in lines:
            if line.startswith('parent '):
                parent = line.split()[1]
                break
        current = parent
    return history