from pathlib import Path

from internetspedd import PAGE


output_dir = Path("public")
output_dir.mkdir(parents=True, exist_ok=True)
(output_dir / "index.html").write_text(PAGE, encoding="utf-8")
print("Generated public/index.html from internetspedd.py.")
