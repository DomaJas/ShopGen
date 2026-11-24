# -*- coding: utf-8 -*-
import json, os, re, datetime, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

import sys
BASE = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(BASE, "shopgen_config.json")
NAMES = os.path.join(BASE, "names_ru.json")
CUR_ALIAS = {"ore": "ore", "ар": "ore", "ары": "ore", "dia": "dia", "алм": "dia",
             "алмаз": "dia", "алмазы": "dia"}
CUR_NAME = {"ore": "ары", "dia": "алмазы"}


def pretty(s):
    return s.replace("_", " ").capitalize()


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Генератор ассортимента магазина")
        self.root.geometry("1040x680")
        self.tex, self.is_item, self.tex_dir = {}, set(), ""
        self._ph, self.items, self.names = {}, [], {}
        try:
            self.tex_dir = json.load(open(CFG, encoding="utf-8")).get("tex_dir", "")
        except Exception:
            pass
        try:
            self.names = json.load(open(NAMES, encoding="utf-8"))
        except Exception:
            pass
        self.index_tex()
        self.build()

    # ---------- текстуры ----------
    def index_tex(self):
        self.tex, self.is_item = {}, set()
        base = self.tex_dir
        for extra in ("", "textures", "minecraft/textures", "assets/minecraft/textures"):
            if os.path.isdir(os.path.join(base, extra, "item")) or os.path.isdir(os.path.join(base, extra, "items")):
                base = os.path.join(base, extra)
                break
        for sub in ("block", "blocks", "item", "items"):
            d = os.path.join(base, sub)
            if os.path.isdir(d):
                for f in os.listdir(d):
                    if f.lower().endswith(".png"):
                        key = f[:-4]
                        self.tex[key] = os.path.join(d, f)
                        if sub.startswith("item"):
                            self.is_item.add(key)

    def set_tex(self):
        d = filedialog.askdirectory(title="Папка textures ресурс-пака")
        if d:
            self.tex_dir = d
            self.index_tex()
            self._ph.clear()
            json.dump({"tex_dir": d}, open(CFG, "w", encoding="utf-8"))
            self.status(f"Найдено текстур: {len(self.tex)}")

    def photo(self, name, size=32):
        k = (name, size)
        if k not in self._ph:
            try:
                im = Image.open(self.tex[name]).convert("RGBA")
                if im.height > im.width:
                    im = im.crop((0, 0, im.width, im.width))
            except Exception:
                im = Image.new("RGBA", (16, 16), (130, 130, 130, 255))
            self._ph[k] = ImageTk.PhotoImage(im.resize((size, size), Image.NEAREST))
        return self._ph[k]

    def label_for(self, iid):
        return self.names.get(iid) or pretty(iid)

    # ---------- интерфейс ----------
    def build(self):
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Button(top, text="Папка текстур", command=self.set_tex).pack(side="left", padx=2)
        ttk.Button(top, text="Открыть JSON", command=self.load_json).pack(side="left", padx=2)
        ttk.Label(top, text="  Магазин:").pack(side="left")
        self.shop = tk.StringVar(value="Мой магазин")
        ttk.Entry(top, textvariable=self.shop, width=30).pack(side="left", padx=4)
        ttk.Button(top, text="СОХРАНИТЬ JSON", command=self.save_json).pack(side="right")

        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=8)

        # левая панель: форма
        left = ttk.Frame(main, width=330)
        left.pack(side="left", fill="y", padx=(0, 8))
        ttk.Label(left, text="Предмет (id из текстур):").pack(anchor="w")
        self.iid = tk.StringVar()
        e = ttk.Entry(left, textvariable=self.iid, width=38)
        e.pack(anchor="w")
        e.bind("<KeyRelease>", self.suggest)
        self.sug = tk.Listbox(left, height=6, width=38, exportselection=False)
        self.sug.pack(anchor="w")
        self.sug.bind("<<ListboxSelect>>", self.pick_sug)

        ttk.Label(left, text="Название:").pack(anchor="w", pady=(6, 0))
        self.lab = tk.StringVar()
        ttk.Entry(left, textvariable=self.lab, width=38).pack(anchor="w")

        row = ttk.Frame(left)
        row.pack(anchor="w", pady=6)
        ttk.Label(row, text="Цена:").pack(side="left")
        self.price = tk.IntVar(value=1)
        ttk.Spinbox(row, from_=1, to=99999, textvariable=self.price, width=7).pack(side="left", padx=6)
        self.cur = tk.StringVar(value="ore")
        ttk.Radiobutton(row, text="Ары", variable=self.cur, value="ore").pack(side="left")
        ttk.Radiobutton(row, text="Алмазы", variable=self.cur, value="dia").pack(side="left")

        ttk.Label(left, text="Зачарование (необязательно):").pack(anchor="w")
        self.ench = tk.StringVar()
        ttk.Entry(left, textvariable=self.ench, width=38).pack(anchor="w")

        bt = ttk.Frame(left)
        bt.pack(anchor="w", pady=8)
        ttk.Button(bt, text="Добавить", command=self.add).pack(side="left")
        ttk.Button(bt, text="Изменить", command=self.edit).pack(side="left", padx=4)
        ttk.Button(bt, text="Удалить", command=self.delete).pack(side="left")

        ttk.Separator(left).pack(fill="x", pady=8)
        ttk.Label(left, text="Массовое заполнение").pack(anchor="w")
        ttk.Button(left, text="Все предметы из текстур (цена из поля выше)",
                   command=self.bulk_all).pack(fill="x", pady=2)
        ttk.Button(left, text="Вставить список строк…", command=self.bulk_text).pack(fill="x", pady=2)
        ttk.Button(left, text="Очистить весь список", command=self.clear).pack(fill="x", pady=2)

        # правая часть: таблица
        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True)
        style = ttk.Style()
        style.configure("Treeview", rowheight=36)
        self.tv = ttk.Treeview(right, columns=("id", "label", "price", "ench"),
                               show="tree headings", selectmode="browse")
        for c, t, w in (("#0", "", 50), ("id", "id", 170), ("label", "Название", 200),
                        ("price", "Цена", 110), ("ench", "Зачарование", 170)):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=w, stretch=(c != "#0"))
        self.tv.pack(side="left", fill="both", expand=True)
        self.tv.bind("<<TreeviewSelect>>", self.pick)

        self.stat = ttk.Label(self.root, text="")
        self.stat.pack(fill="x", padx=8, pady=4)
        self.refresh()

    def status(self, t):
        self.stat.configure(text=t)

    # ---------- подсказки ----------
    def suggest(self, _=None):
        q = self.iid.get().strip().lower().replace(" ", "_")
        self.sug.delete(0, "end")
        for k in [k for k in sorted(self.tex) if q in k][:40]:
            self.sug.insert("end", k)

    def pick_sug(self, _=None):
        s = self.sug.curselection()
        if s:
            k = self.sug.get(s[0])
            self.iid.set(k)
            self.lab.set(self.label_for(k))

    # ---------- работа с товарами ----------
    def form(self):
        iid = self.iid.get().strip()
        if not iid:
            return None
        if iid not in self.tex and not messagebox.askyesno(
                "Нет текстуры", f"Текстура «{iid}» не найдена. Добавить всё равно?"):
            return None
        return {"id": iid, "label": self.lab.get().strip() or self.label_for(iid),
                "price": self.price.get(), "cur": self.cur.get(), "ench": self.ench.get().strip()}

    def put(self, d):
        for it in self.items:
            if it["id"] == d["id"] and it["ench"] == d["ench"]:
                it.update(d)
                break
        else:
            self.items.append(d)
        self.refresh()

    def add(self):
        d = self.form()
        if d:
            self.put(d)

    def sel_index(self):
        s = self.tv.selection()
        return int(s[0]) if s else None

    def edit(self):
        i, d = self.sel_index(), self.form()
        if i is not None and d:
            self.items[i] = d
            self.refresh()

    def delete(self):
        i = self.sel_index()
        if i is not None:
            del self.items[i]
            self.refresh()

    def clear(self):
        if self.items and messagebox.askyesno("Очистка", "Удалить все товары из списка?"):
            self.items.clear()
            self.refresh()

    def pick(self, _=None):
        i = self.sel_index()
        if i is None:
            return
        it = self.items[i]
        self.iid.set(it["id"]); self.lab.set(it["label"]); self.price.set(it["price"])
        self.cur.set(it["cur"]); self.ench.set(it["ench"])

    def refresh(self):
        self.tv.delete(*self.tv.get_children())
        for n, it in enumerate(self.items):
            self.tv.insert("", "end", iid=str(n), image=self.photo(it["id"]) if it["id"] in self.tex else "",
                           values=(it["id"], it["label"], f'{it["price"]} {CUR_NAME[it["cur"]]}', it["ench"]))
        self.status(f"Товаров в списке: {len(self.items)}")

    # ---------- массовое заполнение ----------
    def bulk_all(self):
        cands = sorted(k for k in self.is_item if k in self.tex)
        have = {(it["id"], it["ench"]) for it in self.items}
        added = 0
        for k in cands:
            if (k, "") not in have:
                self.items.append({"id": k, "label": self.label_for(k), "price": self.price.get(),
                                   "cur": self.cur.get(), "ench": ""})
                added += 1
        self.refresh()
        self.status(f"Добавлено предметов: {added} (пропущены уже существующие)")

    def parse_line(self, line):
        parts = [p.strip() for p in re.split(r"\s*[;\t]\s*", line)] if re.search(r"[;\t]", line) else line.split()
        iid = parts[0]
        if iid not in self.tex:
            raise ValueError(f"нет текстуры «{iid}»")
        price = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else self.price.get()
        cur = CUR_ALIAS.get(parts[2].lower(), "ore") if len(parts) > 2 else self.cur.get()
        label = parts[3] if len(parts) > 3 and parts[3] else self.label_for(iid)
        ench = parts[4] if len(parts) > 4 else ""
        return {"id": iid, "label": label, "price": price, "cur": cur, "ench": ench}

    def bulk_text(self):
        win = tk.Toplevel(self.root)
        win.title("Вставить список")
        win.geometry("560x420")
        ttk.Label(win, text="Одна строка — один товар:\n"
                            "id ; цена ; ар/алм ; название ; зачарование\n"
                            "Всё, кроме id, необязательно. Пример: diamond_sword; 150; алм; Меч; Острота II",
                  justify="left").pack(anchor="w", padx=8, pady=6)
        txt = tk.Text(win, height=16)
        txt.pack(fill="both", expand=True, padx=8)

        def go():
            ok, errs = 0, []
            for n, line in enumerate(txt.get("1.0", "end").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    self.put(self.parse_line(line))
                    ok += 1
                except Exception as ex:
                    errs.append(f"строка {n}: {ex}")
            win.destroy()
            msg = f"Добавлено: {ok}"
            if errs:
                msg += "\n\nОшибки:\n" + "\n".join(errs)
            messagebox.showinfo("Список", msg)

        ttk.Button(win, text="Добавить", command=go).pack(pady=8)

    # ---------- JSON ----------
    def save_json(self):
        if not self.items:
            return messagebox.showwarning("Пусто", "Список товаров пуст.")
        p = filedialog.asksaveasfilename(defaultextension=".json", initialfile="shop.json",
                                         filetypes=[("JSON", "*.json")])
        if not p:
            return
        data = {
            "format": "shop-items",
            "version": 1,
            "generated": datetime.datetime.now().isoformat(timespec="seconds"),
            "shop": {"name": self.shop.get().strip() or "Магазин"},
            "items": [{
                "id": it["id"],
                "minecraft_id": "minecraft:" + it["id"],
                "label": it["label"],
                "price": it["price"],
                "currency": it["cur"],
                "enchant": it["ench"],
            } for it in self.items],
        }
        json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        self.status(f"Сохранено: {p}")

    def load_json(self):
        p = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not p:
            return
        try:
            d = json.load(open(p, encoding="utf-8"))
            self.shop.set(d.get("shop", {}).get("name", "Магазин"))
            self.items = [{"id": x["id"], "label": x.get("label", self.label_for(x["id"])),
                           "price": int(x.get("price", 1)), "cur": x.get("currency", "ore"),
                           "ench": x.get("enchant", "")} for x in d["items"]]
            self.refresh()
        except Exception as ex:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{ex}")


if __name__ == "__main__":
    App().root.mainloop()