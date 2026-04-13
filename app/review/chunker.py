def parse_patch_into_chunks(files: list) -> list:
    chunks = []

    for file in files:
        filename = file.get("filename")
        patch = file.get("patch")

        if not patch:
            continue

        chunks.append({
            "filename": filename,
            "patch": patch,
            "language": detect_language(filename),
            "position_map": build_position_map(patch)
        })

    return chunks


def build_position_map(patch: str) -> dict:
    """Maps line numbers to diff positions for GitHub inline comments."""
    position_map = {}
    position = 0
    current_line = 0

    for line in patch.split("\n"):
        position += 1
        if line.startswith("@@"):
            # Extract the starting line number from @@ -a,b +c,d @@
            import re
            match = re.search(r"\+(\d+)", line)
            if match:
                current_line = int(match.group(1)) - 1
        elif line.startswith("+"):
            current_line += 1
            position_map[current_line] = position
        elif line.startswith("-"):
            pass  # deleted lines don't have a new line number
        else:
            current_line += 1

    return position_map


def detect_language(filename: str) -> str:
    ext = filename.split(".")[-1]
    mapping = {
        "py": "Python",
        "ts": "TypeScript",
        "js": "JavaScript",
        "java": "Java",
        "go": "Go",
        "rs": "Rust",
        "cs": "C#",
        "cpp": "C++",
    }
    return mapping.get(ext, "Unknown")