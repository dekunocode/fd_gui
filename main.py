import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import platform

class FdSearchApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("fd ファイル検索ツール")
        self.geometry("800x600")
        self.create_widgets()

    def create_widgets(self):
        # 検索フォルダ選択
        folder_frame = ttk.Frame(self)
        folder_frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(folder_frame, text="検索フォルダ:").pack(side="left")
        self.folder_var = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self.folder_var, width=50).pack(side="left", padx=5)
        ttk.Button(folder_frame, text="参照", command=self.browse_folder).pack(side="left")

        # キーワード入力
        keyword_frame = ttk.Frame(self)
        keyword_frame.pack(padx=10, pady=(0, 10), fill="x")

        ttk.Label(keyword_frame, text="検索キーワード（正規表現）:").pack(side="left")
        self.keyword_var = tk.StringVar()
        ttk.Entry(keyword_frame, textvariable=self.keyword_var, width=40).pack(side="left", padx=5)

        # ファイル種別選択
        type_frame = ttk.LabelFrame(self, text="ファイル種別")
        type_frame.pack(padx=10, pady=5, fill="x")
        self.type_var = tk.StringVar(value="all")
        for text, val in [("すべて", "all"), ("ファイルのみ", "f"), ("ディレクトリのみ", "d")]:
            ttk.Radiobutton(type_frame, text=text, value=val, variable=self.type_var).pack(side="left", padx=10)

        # 隠しファイル含むチェック
        self.include_hidden_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self, text="隠しファイルも含める（-H）", variable=self.include_hidden_var).pack(padx=10, anchor="w")

        # 検索ボタン
        self.search_button = ttk.Button(self, text="検索", command=self.start_search)
        self.search_button.pack(pady=(5, 10))

        # ステータス表示
        self.status_var = tk.StringVar(value="準備完了")
        self.status_label = ttk.Label(self, textvariable=self.status_var, foreground="blue")
        self.status_label.pack(padx=10, anchor="w")

        # 検索結果とスクロールバーを同じフレームに配置
        result_frame = ttk.Frame(self)
        result_frame.pack(padx=10, fill="both", expand=True)

        # 検索結果リスト
        self.result_listbox = tk.Listbox(result_frame)
        self.result_listbox.pack(side="left", fill="both", expand=True)
        self.result_listbox.bind("<Double-Button-1>", self.open_selected_path)

        # スクロールバー（縦）
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.result_listbox.config(yscrollcommand=scrollbar.set)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)

    def start_search(self):
        self.search_button.config(state="disabled", text="検索中...")
        self.status_var.set("🔍 検索中...")
        self.result_listbox.delete(0, "end")
        threading.Thread(target=self.run_fd_search, daemon=True).start()

    def run_fd_search(self):
        folder = self.folder_var.get()
        keyword = self.keyword_var.get().strip()
        fd_path = "./fd.exe"  # fd 実行ファイルのパス

        if not os.path.isdir(folder):
            self.show_error("検索フォルダが存在しません。")
            return
        if not keyword:
            self.show_error("検索キーワードを入力してください。")
            return
        if not os.path.isfile(fd_path):
            self.show_error("fd.exe が見つかりません。アプリと同じフォルダに配置してください。")
            return

        cmd = [fd_path, keyword, folder, "--absolute-path"]
        if self.type_var.get() in ("f", "d"):
            cmd += ["-t", self.type_var.get()]
        if self.include_hidden_var.get():
            cmd.append("-H")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            if result.returncode == 0:
                files = result.stdout.strip().splitlines()
                self.after(0, lambda: self.show_results(files))
            else:
                self.show_error(f"fd 実行エラー:\n{result.stderr}")
        except Exception as e:
            self.show_error(f"エラーが発生しました: {e}")
        finally:
            self.after(0, lambda: self.search_button.config(state="normal", text="検索"))

    def show_results(self, files):
        if not files or files == ['']:
            self.result_listbox.insert("end", "一致するファイルは見つかりませんでした。")
            self.status_var.set("⚠ 一致するファイルはありませんでした。")
        else:
            for f in files:
                self.result_listbox.insert("end", f)
            self.status_var.set(f"✅ 検索完了（{len(files)}件）")

    def open_selected_path(self, event=None):
        selection = self.result_listbox.curselection()
        if not selection:
            return
        path = self.result_listbox.get(selection[0])
        if os.path.exists(path):
            try:
                if platform.system() == "Windows":
                    os.startfile(path)
                elif platform.system() == "Darwin":
                    subprocess.run(["open", path])
                else:
                    subprocess.run(["xdg-open", path])
            except Exception as e:
                messagebox.showerror("エラー", f"ファイルを開けませんでした: {e}")

    def show_error(self, msg):
        self.after(0, lambda: messagebox.showerror("エラー", msg))
        self.after(0, lambda: self.search_button.config(state="normal", text="検索"))
        self.after(0, lambda: self.status_var.set("❌ エラーが発生しました"))

if __name__ == "__main__":
    app = FdSearchApp()
    app.mainloop()
