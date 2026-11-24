"""Shot 3 of the automation video: the real price monitor (venta_kamas/interfaz.pyw), captured state by state.

    python scripts/media/record_app.py

Safe by construction: prices are simulated (no request to the buyer site), the seller is replaced by a stub (no
browser, no sale), the server list and the sale details live in temporary files (the real datos_venta.json, with
personal data, is never read) and the sales log reads as empty.

The window is drawn at 2x (Tk scaling + every pixel size doubled) so the video can zoom in and stay sharp. A 2x
window doesn't fit the 1280x1024 screen and Tk only paints what is on screen, so each state is captured in tiles:
the window is moved so each part is on screen in turn, and the tiles are stitched. The video is made from these
states (automation_assemble.py app), with a drawn mouse pointer and the server and game names blurred.
Writes out/portfolio-automation-overview/app/<state>.png and app/meta.json (widget boxes, client coordinates).
"""
from __future__ import annotations

import ctypes
import importlib.machinery
import json
import sys
import tempfile
import time
import types
from ctypes import wintypes
from pathlib import Path

from PIL import Image, ImageGrab

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
APP_DIR = ROOT / "venta_kamas"
OUT = HERE / "out/portfolio-automation-overview/app"
K = 2                                   # draw scale
SIZE = (1080 * K, 720 * K)

ctypes.windll.shcore.SetProcessDpiAwareness(2)
sys.path.insert(0, str(APP_DIR))
ui = importlib.machinery.SourceFileLoader("interfaz", str(APP_DIR / "interfaz.pyw")).load_module()
tk, ttk = ui.tk, ui.ttk

# ── safety: nothing real is read, written or sent ─────────────────────────────────────────────────────────
tmp = Path(tempfile.mkdtemp(prefix="venta_kamas_demo_"))
EXISTING = [{"servidor": "Servidor2", "precio_min": "4.2", "millones": "25"},
            {"servidor": "Servidor4", "precio_min": "2.9", "millones": "60"}]
(tmp / "servidores.json").write_text(json.dumps(EXISTING), encoding="utf-8")
(tmp / "datos.json").write_text(json.dumps({"metodo_pago": "usdt", "beneficiario": "Demo",
                                            "direccion_trc20": "TDemo000000000000000000000000000000"}), encoding="utf-8")
ui.FICHERO_SERVIDORES = tmp / "servidores.json"
ui.FICHERO_DATOS_VENTA = tmp / "datos.json"
ui.registro.FICHERO = tmp / "ventas.csv"
ui.registro.leer_todo = lambda: []


class NoSeller:                         # replaces vendedor.Vendedor: never opens a browser
    def __init__(self, *a, **k): ...
    def pedir_venta(self, *a, **k): raise SystemExit("a sale was requested during the demo recording")
    def pedir_login(self, *a, **k): raise SystemExit("login requested during the demo recording")
    def cerrar(self): ...


ui.Vendedor = NoSeller
ui.lector_precios.descargar_config = lambda *a, **k: (_ for _ in ()).throw(SystemExit("network read attempted"))
ui.App._bucle_precios = lambda self, parar: None       # readings are pushed by this script instead

NEW = ("Servidor1", "3.5", "40")       # the server the video adds (blurred), target price, millions


def cfg(prices: dict[str, float]) -> dict:
    return {"servers": {n: {"open": True, "game": ui.juego_de(n)[1],
                            "prices": {"Usdt": {"p": p, "o": True, "s": "USDT"}}} for n, p in prices.items()},
            "minimums": {}}


READINGS = [{"Servidor2": 3.981, "Servidor4": 2.744, "Servidor1": 3.412},
            {"Servidor2": 3.995, "Servidor4": 2.761, "Servidor1": 3.437},
            {"Servidor2": 4.012, "Servidor4": 2.752, "Servidor1": 3.468}]


# ── 2x drawing ───────────────────────────────────────────────────────────────────────────────────────────
def scale_style(root) -> None:
    st = ttk.Style(root)
    def mul(v):
        if isinstance(v, (tuple, list)):
            return tuple(int(x) * K for x in v)
        return int(str(v).split()[0]) * K if str(v).strip() else v
    for style, opts in {"TNotebook": ["tabmargins"], "TNotebook.Tab": ["padding"], "TButton": ["padding"],
                        "Primario.TButton": [], "TEntry": ["padding"], "TCombobox": ["padding", "arrowsize"],
                        "Treeview": ["rowheight"], "Treeview.Heading": ["padding"],
                        "Vertical.TScrollbar": ["arrowsize"]}.items():
        for o in opts:
            v = st.lookup(style, o)
            if v not in ("", None):
                parts = str(v).split()
                st.configure(style, **{o: tuple(int(float(x)) * K for x in parts) if len(parts) > 1 else int(float(parts[0])) * K})


def scale_tree(w) -> None:
    """Double every pixel distance given as a plain number: frame heights, label padding, pack/grid padding,
    ttk padding and highlight borders."""
    def two(v):
        if v in ("", None):
            return v
        if isinstance(v, (tuple, list)):
            return tuple(int(float(str(x))) * K for x in v)
        parts = str(v).split()
        return tuple(int(float(x)) * K for x in parts) if len(parts) > 1 else int(float(parts[0])) * K
    if isinstance(w, (tk.Frame, tk.Label)):
        for o in ("padx", "pady", "highlightthickness") + (("height",) if isinstance(w, tk.Frame) else ()):
            try:
                w[o] = two(w[o])
            except tk.TclError:
                pass
    elif isinstance(w, ttk.Frame):
        try:
            if str(w["padding"]):
                w["padding"] = two(w["padding"])
        except tk.TclError:
            pass
    mgr = w.winfo_manager()
    if mgr == "pack":
        i = w.pack_info()
        w.pack_configure(padx=two(i.get("padx", 0)), pady=two(i.get("pady", 0)))
    elif mgr == "grid":
        i = w.grid_info()
        w.grid_configure(padx=two(i.get("padx", 0)), pady=two(i.get("pady", 0)))
    for c in w.winfo_children():
        scale_tree(c)


# ── tiled capture ────────────────────────────────────────────────────────────────────────────────────────
def work_area() -> tuple[int, int, int, int]:
    r = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)
    return r.left, r.top, r.right, r.bottom


def capture(root, post=None) -> Image.Image:
    """The client area, stitched from tiles. `post()` re-opens a popup after each move (it stays where it was)."""
    wl, wt, wr, wb = work_area()
    canvas = Image.new("RGB", SIZE, (255, 0, 255))
    root.update()
    fx, fy = root.winfo_rootx() - root.winfo_x(), root.winfo_rooty() - root.winfo_y()   # frame borders
    xs = sorted({0, -(SIZE[0] - (wr - wl))})
    ys = sorted({0, -(SIZE[1] - (wb - wt))})
    for oy in ys:
        for ox in xs:
            root.geometry(f"+{wl + ox - fx}+{wt + oy - fy}")
            root.update()
            if post:
                post()
            root.update()
            time.sleep(0.25)
            root.update()
            cx, cy = root.winfo_rootx(), root.winfo_rooty()
            box = (max(cx, wl), max(cy, wt), min(cx + SIZE[0], wr), min(cy + SIZE[1], wb))
            canvas.paste(ImageGrab.grab(bbox=box), (box[0] - cx, box[1] - cy))
    root.geometry(f"+{wl - fx}+{wt - fy}")
    root.update()
    return canvas


def rel(root, w, inset=0) -> list[int]:
    w.update_idletasks()
    x, y = w.winfo_rootx() - root.winfo_rootx(), w.winfo_rooty() - root.winfo_rooty()
    return [x + inset, y + inset, x + w.winfo_width() - inset, y + w.winfo_height() - inset]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    root.tk.call("tk", "scaling", K * 96 / 72)
    root.wm_maxsize(5000, 5000)
    root.title("Venta automática")
    root.attributes("-topmost", True)
    ui.aplicar_estilo(root)
    scale_style(root)
    for c, (h, wdt, a) in list(ui.COLS_SRV.items()):
        ui.COLS_SRV[c] = (h, wdt * K, a)
    app = ui.App(root)
    scale_tree(app)
    root.geometry(f"{SIZE[0]}x{SIZE[1]}+0+0")
    # the buyer site is never named: drop it from the header; the footer keeps only the reading interval
    for w in app.winfo_children():
        for l in [w, *w.winfo_children(), *[g for c in w.winfo_children() for g in c.winfo_children()]]:
            if isinstance(l, tk.Label):
                t = l.cget("text")
                if t == "Venta automática":                     # the currency's name gives the game away
                    l.config(text="Venta automática")
                elif "sitio-comprador" in t:
                    l.config(text="Monitor de precios y venta asistida")
                elif t.startswith("Lectura cada"):
                    l.config(text=f"Lectura cada {ui.INTERVALO_S} s")
    for e in (app.ent_precio, app.ent_millones):
        e.configure(cursor="arrow")
    root.update()

    meta = {"size": SIZE, "scale": K, "states": [], "boxes": {}}
    tv = app.tabla_srv

    def shot(name, post=None):
        img = capture(root, post)
        img.save(OUT / f"{name}.png")
        cells = []
        for item in tv.get_children():
            for col in ("servidor", "juego"):
                b = tv.bbox(item, col)
                if b:
                    x0, y0, x1, y1 = rel(root, tv)
                    cells.append([x0 + b[0], y0 + b[1], x0 + b[0] + b[2], y0 + b[1] + b[3]])
        meta["states"].append({"name": name, "blur": cells})
        print("state", name)

    B = meta["boxes"]
    B["combo"] = rel(root, app.cmb_srv)
    B["precio"] = rel(root, app.ent_precio)
    B["millones"] = rel(root, app.ent_millones)
    B["monitor"] = rel(root, app.btn_monitor)
    add_btn = next(w for w in app.ent_millones.master.winfo_children()
                   if isinstance(w, ttk.Button) and w.cget("text") == "Añadir")
    B["add"] = rel(root, add_btn)
    B["table"] = rel(root, tv)
    B["kpis"] = rel(root, app.kpi["vigilados"].master.master.master)
    B["pill"] = rel(root, app.pastilla)

    shot("00-start")

    # dropdown open, the new server highlighted
    values = list(app.cmb_srv.cget("values"))
    idx = next(i for i, v in enumerate(values) if v.startswith(NEW[0]))
    pd = root.tk.call("ttk::combobox::PopdownWindow", str(app.cmb_srv))
    lb = f"{pd}.f.l"

    def post():
        if str(root.tk.call("winfo", "ismapped", pd)) != "1":
            root.tk.call("ttk::combobox::Post", str(app.cmb_srv))
            root.update()
        cb = app.cmb_srv
        root.tk.call("wm", "geometry", pd, f"+{cb.winfo_rootx()}+{cb.winfo_rooty() + cb.winfo_height()}")
        root.tk.call(lb, "selection", "clear", 0, "end")
        root.tk.call(lb, "selection", "set", idx)
        root.tk.call(lb, "activate", idx)
        root.tk.call("wm", "attributes", pd, "-topmost", 1)
        root.update()
        print("  popdown", root.tk.call("winfo", "ismapped", pd), root.tk.call("winfo", "geometry", pd))
    shot("01-dropdown", post)
    if "--dropdown-only" in sys.argv: return
    wi = lambda what: int(root.tk.call("winfo", what, pd))
    px, py = wi("rootx") - root.winfo_rootx(), wi("rooty") - root.winfo_rooty()
    pw_, ph_ = wi("width"), wi("height")
    rows = []
    for i in range(len(values)):
        bx = root.tk.call(lb, "bbox", i)
        if bx:
            x, y, w_, h_ = map(int, str(bx).split()) if isinstance(bx, str) else map(int, bx)
            rows.append([px + 2, py + y + 1, px + pw_ - 2, py + y + h_ + 3])
    B["dropdown_rows"] = rows
    B["dropdown_target"] = rows[idx]
    meta["states"][-1]["blur"] += [[px, py, px + pw_, py + ph_]]
    root.tk.call("ttk::combobox::Unpost", str(app.cmb_srv))
    root.update()

    app.cmb_srv.set(values[idx])
    shot("02-selected")
    meta["states"][-1]["blur"].append(B["combo"])

    def typing(entry, text, tag):
        entry.focus_set()
        ttk.Style(root).configure("TEntry", insertwidth=0)   # a blinking caret would flicker between states
        for n in range(1, len(text) + 1):
            entry.delete(0, "end"); entry.insert(0, text[:n])
            shot(f"{tag}-{n}")
            meta["states"][-1]["blur"].append(B["combo"])
    typing(app.ent_precio, NEW[1], "03-price")
    typing(app.ent_millones, NEW[2], "04-millions")

    app._anadir_srv()
    root.focus_set()
    shot("05-added")
    app._toggle_monitoreo()
    shot("06-monitoring")
    from datetime import datetime, timedelta
    t0 = datetime.now().replace(second=11, microsecond=0)
    for n, r in enumerate(READINGS):
        app._con_precios(cfg(r))
        app.ultima_lectura = t0 + timedelta(minutes=n)
        app._refrescar_kpis()
        app._avisar(f"Precios actualizados a las {app.ultima_lectura:%H:%M:%S}.")
        shot(f"07-reading-{n + 1}")
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    root.destroy()
    print("->", OUT)


if __name__ == "__main__":
    main()
