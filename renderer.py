import subprocess
from pathlib import Path

import config


def run_plantuml(puml_path: Path) -> tuple[int, str]:
    """Pokrece plantuml.jar i generise PNG dijagram."""
    cmd = ["java", "-jar", str(config.PLANTUML_JAR), "-tpng", str(puml_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, (result.stderr or "") + (result.stdout or "")
