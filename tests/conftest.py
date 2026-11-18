import os
import sys
import tempfile
from pathlib import Path

# Données de test isolées (avant tout import de clipforge).
_TMP = tempfile.mkdtemp(prefix="clipforge-tests-")
os.environ["CLIPFORGE_DATA"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
