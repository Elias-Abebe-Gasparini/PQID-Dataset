from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    notebook_path = Path(__file__).with_name("plot_quantitative_figures.ipynb")
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    namespace: dict[str, object] = {"__name__": "__main__"}

    for index, cell in enumerate(notebook["cells"]):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if not source.strip():
            continue
        print(f"running {notebook_path.name} cell {index}")
        exec(compile(source, f"{notebook_path}:cell-{index}", "exec"), namespace)

    from sync_manuscript_figure_labels import sync_manuscript_figure_labels

    for target in sync_manuscript_figure_labels():
        print(f"synced {target}")


if __name__ == "__main__":
    main()
