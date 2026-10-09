import json
import subprocess


def send_b2b_invitation(email, display_name, script_path):
    command = [
        "powershell.exe",
        "-File",
        script_path,
        "-Email",
        email,
        "-DisplayName",
        display_name
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError("B2B invitation failed")

    output_lines = result.stdout.strip().splitlines()

    for line in reversed(output_lines):
        line = line.strip()

        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)

    raise RuntimeError("No invitation result returned")