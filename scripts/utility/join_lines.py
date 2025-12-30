import sys


def truncate_content(content: str) -> str:
    frontmatter = ""
    body = content
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = '---' + parts[1] + '---\n'
            body = parts[2]

    return frontmatter + ' '.join(body.split())


def truncate_file(src_file: str, dest_file: str) -> None:
    with open(src_file, 'r', encoding='utf-8') as f:
        content = f.read()

    result = truncate_content(content)

    with open(dest_file, 'w', encoding='utf-8') as f:
        f.write(result)

