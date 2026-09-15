from pathlib import Path
import sys
platform = next(p / '플랫폼코드' for p in Path(__file__).resolve().parents if (p / '플랫폼코드' / 'hydops').is_dir())
sys.path.insert(0, str(platform))
