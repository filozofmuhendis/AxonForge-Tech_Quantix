import os
import re

search_patterns = {
    "localhost": r"localhost",
    "loopback": r"127\.0\.0\.1",
    "todo": r"TODO",
    "fixme": r"FIXME",
    "mock": r"mock",
    "dummy": r"dummy",
    "fake": r"fake",
    "sqlite": r"sqlite",
}

exclude_dirs = {".git", ".next", "node_modules", ".pytest_cache", "venv", "__pycache__"}
exclude_files = {"scan_repo.py", "package-lock.json", "yarn.lock"}

results = []

for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for file in files:
        if file in exclude_files or file.endswith(".png") or file.endswith(".ico"):
            continue
        filepath = os.path.join(root, file)
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                for key, pattern in search_patterns.items():
                    matches = list(re.finditer(pattern, content, re.IGNORECASE))
                    if matches:
                        for match in matches:
                            line_num = content.count("\n", 0, match.start()) + 1
                            line_content = content.split("\n")[line_num - 1].strip()
                            results.append({
                                "file": filepath,
                                "line": line_num,
                                "type": key,
                                "content": line_content[:150]
                            })
        except Exception as e:
            pass

print(f"Total findings: {len(results)}")
for r in results[:100]:  # Limit output to first 100
    print(f"{r['file']}:{r['line']} [{r['type'].upper()}]: {r['content']}")
