"""Render the note's three equations without a browser or external math service."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


OUTPUT = Path(__file__).resolve().parents[1]


def render(name, rows, height):
    fig = plt.figure(figsize=(11, height))
    artists = [fig.text(x, y, text, fontsize=size, va="center")
               for x, y, text, size in rows]
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = [artist.get_window_extent(renderer) for artist in artists]
    for i, box in enumerate(boxes):
        for other in boxes[i + 1:]:
            if box.overlaps(other):
                raise ValueError(f"overlapping equation elements: {name}")
    for extension in ("png", "svg"):
        metadata = {"Software": "HydroOpsLM equation renderer"} if extension == "png" else {"Date": None}
        fig.savefig(OUTPUT / f"{name}.{extension}", dpi=180,
                    bbox_inches="tight", pad_inches=0.12, metadata=metadata)
        if extension == "svg":
            target = OUTPUT / f"{name}.svg"
            text = target.read_text(encoding="utf-8")
            target.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n",
                              encoding="utf-8", newline="\n")
    plt.close(fig)


if __name__ == "__main__":
    plt.rcParams.update({"svg.hashsalt": "HydroOpsLM-note-equations-v1"})
    render("note-storage-balance", [
        (0, 0.5, r"$S_{t+1}=S_t+Q_{in,t}\Delta t-R_{impl,t}\Delta t-V_{spill,t}-V_{evap,t}-V_{seep,t}.$", 18)
    ], 0.6)
    render("note-capacity-ratio", [
        (0, 0.5, r"$\gamma=\frac{C}{\bar q\times86{,}400\times365.25}.$", 18)
    ], 0.8)
    render("note-rule-release", [
        (0, 0.48, r"$R^*_t=$", 18),
        (0.07, 0.48, "{", 58),
        (0.12, 0.73, r"$k\bar q,$", 18),
        (0.12, 0.25, r"$(\gamma/0.5)^2k\bar q+[1-(\gamma/0.5)^2]Q_{in,t},$", 18),
        (0.70, 0.73, r"$\gamma\geq0.5,$", 18),
        (0.70, 0.25, r"$0\leq\gamma<0.5.$", 18)
    ], 1.3)
