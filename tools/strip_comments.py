import os
import re
import sys
import tokenize
from io import BytesIO
from typing import Iterable


PY_EXTS = {".py"}
HTML_EXTS = {".html", ".htm", ".jinja", ".jinja2"}
JS_EXTS = {".js"}
CSS_EXTS = {".css"}


def strip_python_comments(source: bytes) -> bytes:
    out_tokens = []
    try:
        for tok in tokenize.tokenize(BytesIO(source).readline):
            if tok.type == tokenize.COMMENT:
                continue
                                                                         
            out_tokens.append(tok)
        return tokenize.untokenize(out_tokens)
    except tokenize.TokenError:
        return source


def strip_html_jinja_comments(text: str) -> str:
                                     
    text = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
                                       
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return text


def strip_js_comments(text: str) -> str:
                      
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
                                                                       
    lines = []
    for line in text.splitlines(True):
        if re.match(r"^\s*//", line):
            continue
        lines.append(line)
    return "".join(lines)


def strip_css_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def iter_files(root: str) -> Iterable[str]:
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in filenames:
            yield os.path.join(dirpath, fname)


def process_file(path: str) -> bool:
    _, ext = os.path.splitext(path)
    try:
        if ext in PY_EXTS:
            with open(path, "rb") as f:
                original = f.read()
            processed = strip_python_comments(original)
            if processed != original:
                with open(path, "wb") as f:
                    f.write(processed)
                return True
            return False
        elif ext in HTML_EXTS:
            with open(path, "r", encoding="utf-8") as f:
                original_t = f.read()
            processed_t = strip_html_jinja_comments(original_t)
            if processed_t != original_t:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(processed_t)
                return True
            return False
        elif ext in JS_EXTS:
            with open(path, "r", encoding="utf-8") as f:
                original_t = f.read()
            processed_t = strip_js_comments(original_t)
            if processed_t != original_t:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(processed_t)
                return True
            return False
        elif ext in CSS_EXTS:
            with open(path, "r", encoding="utf-8") as f:
                original_t = f.read()
            processed_t = strip_css_comments(original_t)
            if processed_t != original_t:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(processed_t)
                return True
            return False
        else:
            return False
    except Exception:
        return False


def main() -> int:
    roots = ["app", "api", "."]
    changed = 0
    for root in roots:
        if not os.path.exists(root):
            continue
        for path in iter_files(root):
                                                             
            if any(skip in path for skip in (".venv", os.sep+".git"+os.sep, os.sep+"instance"+os.sep)):
                continue
            if os.sep+"static"+os.sep in path and (path.endswith(".png") or path.endswith(".jpg") or path.endswith(".jpeg") or path.endswith(".svg") or path.endswith(".pdf")):
                continue
            if process_file(path):
                changed += 1
    print(f"OK - arquivos alterados: {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


