#!/usr/bin/env python3

import re
import subprocess
from pathlib import Path


REPOSITORY = Path.cwd()

OUTPUT_PATH = Path(
    "evidence/phase7/"
    "P7-E85_TC013-Repository-Secret-Scan.txt"
)

PROHIBITED_FILENAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
}

PROHIBITED_SUFFIXES = {
    ".pem",
    ".key",
    ".pfx",
    ".p12",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".zip",
    ".7z",
}

SECRET_PATTERNS = {
    "private key material": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
    "Bearer credential": re.compile(
        r"(?i)\bAuthorization\s*:\s*Bearer\s+"
        r"[A-Za-z0-9._~+/=-]{20,}"
    ),
    "JWT-like token": re.compile(
        r"\beyJ[A-Za-z0-9_-]{10,}\."
        r"[A-Za-z0-9_-]{10,}\."
        r"[A-Za-z0-9_-]{10,}\b"
    ),
    "GitHub token": re.compile(
        r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b"
        r"|\bgithub_pat_[A-Za-z0-9_]{30,}\b"
    ),
    "Azure storage account key": re.compile(
        r"(?i)\bAccountKey=[A-Za-z0-9+/=]{40,}"
    ),
}

QUOTED_ASSIGNMENT = re.compile(
    r"""(?ix)
    ["']?
    (
        client[_-]?secret
        |
        access[_-]?token
        |
        temporary[_-]?password
        |
        password
    )
    ["']?
    \s*[:=]\s*
    ["']
    ([^"'\r\n]{8,})
    ["']
    """
)

ENV_ASSIGNMENT = re.compile(
    r"""(?imx)
    ^\s*
    (
        CLIENT_SECRET
        |
        ACCESS_TOKEN
        |
        TEMPORARY_PASSWORD
        |
        PASSWORD
    )
    \s*=\s*
    ([^\s\#]+)
    """
)

SAFE_PLACEHOLDER_WORDS = {
    "example",
    "placeholder",
    "replace",
    "redacted",
    "your_",
    "your-",
    "enter_",
    "enter-",
    "not-recorded",
    "not_recorded",
    "changeme",
}


def get_candidate_files():
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        check=True,
        capture_output=True,
    )

    return [
        Path(item.decode("utf-8"))
        for item in result.stdout.split(b"\0")
        if item
    ]


def is_safe_placeholder(value):
    normalized = value.strip().lower()

    return any(
        marker in normalized
        for marker in SAFE_PLACEHOLDER_WORDS
    )


def main():
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidate_files = get_candidate_files()

    unsafe_files = []
    secret_findings = []
    text_files_scanned = 0
    binary_files_skipped = 0

    for relative_path in candidate_files:
        full_path = REPOSITORY / relative_path

        if not full_path.is_file():
            continue

        lower_name = relative_path.name.lower()
        lower_suffix = relative_path.suffix.lower()

        if (
            lower_name in PROHIBITED_FILENAMES
            or lower_suffix in PROHIBITED_SUFFIXES
        ):
            unsafe_files.append(str(relative_path))

        data = full_path.read_bytes()

        if b"\0" in data:
            binary_files_skipped += 1
            continue

        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            binary_files_skipped += 1
            continue

        text_files_scanned += 1

        for description, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                secret_findings.append(
                    f"{relative_path} | {description}"
                )

        for match in QUOTED_ASSIGNMENT.finditer(text):
            value = match.group(2)

            if not is_safe_placeholder(value):
                secret_findings.append(
                    f"{relative_path} | "
                    "possible hard-coded credential"
                )

        for match in ENV_ASSIGNMENT.finditer(text):
            value = match.group(2).strip("\"'")

            if not is_safe_placeholder(value):
                secret_findings.append(
                    f"{relative_path} | "
                    "possible environment credential"
                )

    unsafe_files = sorted(set(unsafe_files))
    secret_findings = sorted(set(secret_findings))

    passed = (
        len(unsafe_files) == 0
        and len(secret_findings) == 0
    )

    report = [
        "Sunhaven TC-013 repository secret scan",
        "----------------------------------------",
        (
            "Scope: Git-tracked files and non-ignored "
            "untracked files"
        ),
        f"Candidate files examined: {len(candidate_files)}",
        f"Text files scanned: {text_files_scanned}",
        f"Binary files skipped: {binary_files_skipped}",
        f"Unsafe repository files: {len(unsafe_files)}",
        f"Secret findings: {len(secret_findings)}",
        "",
        "Unsafe repository-file findings:",
    ]

    if unsafe_files:
        report.extend(
            f"FAIL | {path}"
            for path in unsafe_files
        )
    else:
        report.append("None")

    report.extend([
        "",
        "Potential secret findings:",
    ])

    if secret_findings:
        report.extend(
            f"REVIEW | {finding}"
            for finding in secret_findings
        )
    else:
        report.append("None")

    report.extend([
        "",
        "Secret values printed by scanner: No",
        f"Result: {'PASS' if passed else 'FAIL'}",
    ])

    OUTPUT_PATH.write_text(
        "\n".join(report) + "\n",
        encoding="utf-8",
    )

    print("\n".join(report))

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
