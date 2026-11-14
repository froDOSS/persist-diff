"""Collect scheduled tasks and the commands they run."""
import os
import subprocess
import xml.etree.ElementTree as ET

SYSTEM32_DIR = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
TASKS_DIR = os.path.join(SYSTEM32_DIR, "Tasks")
NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


def task_command(root):
    commands = []
    for ex in root.findall("t:Actions/t:Exec", NS):
        cmd = ex.findtext("t:Command", default="", namespaces=NS)
        args = ex.findtext("t:Arguments", default="", namespaces=NS)
        commands.append(f"{cmd} {args}".strip())
    return " | ".join(commands) if commands else "(no command)"


def read_task(path):
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return None
    return task_command(root)


def collect_from_scheduler():
    # The scheduler can list tasks visible to accounts that cannot read the Tasks directory.
    command = [os.path.join(SYSTEM32_DIR, "schtasks.exe"), "/Query", "/XML", "ONE"]
    try:
        query = subprocess.run(command, capture_output=True, check=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as error:
        raise OSError("Could not query Windows Task Scheduler.") from error
    try:
        root = ET.fromstring(query.stdout)
    except ET.ParseError as error:
        raise ValueError("Windows Task Scheduler returned invalid XML.") from error
    if root.tag != "Tasks":
        raise ValueError("Windows Task Scheduler returned an unexpected XML format.")

    results = {}
    for task in root:
        uri = task.findtext("t:RegistrationInfo/t:URI", default="", namespaces=NS)
        if not uri.startswith("\\") or uri == "\\":
            raise ValueError("Windows Task Scheduler returned a task without a valid path.")
        key = f"Task{uri}"
        if key in results:
            raise ValueError("Windows Task Scheduler returned a duplicate task path.")
        results[key] = task_command(task)
    return results


def collect():
    try:
        with os.scandir(TASKS_DIR):
            pass
    except OSError:
        return collect_from_scheduler()

    results = {}
    for folder, _, files in os.walk(TASKS_DIR):
        for name in files:
            full = os.path.join(folder, name)
            command = read_task(full)
            if command is not None:
                task = os.path.relpath(full, TASKS_DIR)
                results[f"Task\\{task}"] = command
    return results


if __name__ == "__main__":
    for location, command in collect().items():
        print(location)
        print("    " + command)
