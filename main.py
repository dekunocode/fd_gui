import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import subprocess
import threading
import os
import platform
import sys
import time
import json # ★ 追加
from collections import deque

def resource_path(relative_path: str) -> str:
    """
    実行環境に応じてリソースファイルへの絶対パスを解決して返す。
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class FdSearchApp(ttk.Window):
    """fdコマンドのGUIラッパーアプリケーションのメインウィンドウクラス。"""

    # ★★★★★ ここからが変更箇所 ★★★★★

    def __init__(self):
        self.settings_file = resource_path('settings.json')
        settings = self.load_settings()
        initial_theme = settings.get('theme', 'superhero')

        super().__init__(themename=initial_theme)
        self.title("fd ファイル検索ツール")
        self.geometry("800x630")

        # --- インスタンス変数 ---
        self.search_process = None
        self.results_queue = deque()
        self.update_job = None
        self.found_count = 0

        # --- ウィジェットの作成 ---
        self.set_icon()
        self.create_context_menu()
        self.create_widgets()

        # --- 設定の適用と終了処理 ---
        self.apply_settings(settings)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_settings(self) -> dict:
        """設定ファイル(settings.json)を読み込む。"""
        if not os.path.exists(self.settings_file):
            return {}
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"設定ファイルを読み込めませんでした: {e}")
            return {}

    def save_settings(self):
        """現在の設定を設定ファイル(settings.json)に保存する。"""
        settings_data = {
            'theme': self.style.theme.name,
            'folder': self.folder_var.get(),
            'hidden': self.include_hidden_var.get(),
            'case_sensitive': self.case_sensitive_var.get(),
        }
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"設定ファイルを保存できませんでした: {e}")

    def apply_settings(self, settings: dict):
        """読み込んだ設定をUIに適用する。"""
        self.folder_var.set(settings.get('folder', ''))
        self.include_hidden_var.set(settings.get('hidden', False))
        self.case_sensitive_var.set(settings.get('case_sensitive', False))
        self.on_keyword_change()

    def on_closing(self):
        """ウィンドウが閉じられるときに設定を保存して終了する。"""
        self.save_settings()
        self.destroy()

    # ★★★★★ ここまでが変更箇所 ★★★★★

    def set_icon(self):
        icon_path = resource_path('icon/icon.ico')
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                print(f"アイコンを設定できませんでした: {e}")

    def create_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="この場所をエクスプローラーで開く", command=self.open_file_location)
        self.context_menu.add_command(label="パスをコピー", command=self.copy_path_to_clipboard)

    def create_widgets(self):
        self.create_menu()
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=BOTH, expand=True)
        self.create_settings_widgets(main_frame)
        self.create_options_widgets(main_frame)
        self.search_button = ttk.Button(main_frame, text="検索開始", command=self.start_search, bootstyle=(SUCCESS, OUTLINE))
        self.search_button.pack(fill=X, pady=10, ipady=5)
        self.search_button.config(state=DISABLED)
        self.create_results_widgets(main_frame)
        self.create_statusbar()

    def create_settings_widgets(self, parent):
        settings_frame = ttk.Frame(parent)
        settings_frame.pack(fill=X, pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        ttk.Label(settings_frame, text="検索フォルダ:").grid(row=0, column=0, padx=(0, 5), sticky=W)
        self.folder_var = tk.StringVar()
        folder_entry = ttk.Entry(settings_frame, textvariable=self.folder_var)
        folder_entry.grid(row=0, column=1, sticky=EW, padx=(0, 5))
        ttk.Button(settings_frame, text="参照", command=self.browse_folder, bootstyle=SECONDARY).grid(row=0, column=2)
        ttk.Label(settings_frame, text="検索キーワード:").grid(row=1, column=0, padx=(0, 5), pady=(5,0), sticky=W)
        self.keyword_var = tk.StringVar()
        self.keyword_var.trace_add("write", self.on_keyword_change)
        keyword_entry = ttk.Entry(settings_frame, textvariable=self.keyword_var)
        keyword_entry.grid(row=1, column=1, columnspan=2, sticky=EW, pady=(5,0))
        keyword_entry.bind("<Return>", self.start_search)

    def create_options_widgets(self, parent):
        options_frame = ttk.LabelFrame(parent, text="検索オプション", padding=10)
        options_frame.pack(fill=X, pady=5)
        type_frame = ttk.Frame(options_frame)
        type_frame.pack(side=LEFT, fill=X, expand=True)
        self.type_var = tk.StringVar(value="all")
        ttk.Radiobutton(type_frame, text="すべて", value="all", variable=self.type_var, bootstyle="outline-toolbutton").pack(side=LEFT, padx=(0,5), expand=True, fill=X)
        ttk.Radiobutton(type_frame, text="ファイルのみ", value="f", variable=self.type_var, bootstyle="outline-toolbutton").pack(side=LEFT, padx=5, expand=True, fill=X)
        ttk.Radiobutton(type_frame, text="ディレクトリのみ", value="d", variable=self.type_var, bootstyle="outline-toolbutton").pack(side=LEFT, padx=5, expand=True, fill=X)
        check_frame = ttk.Frame(options_frame)
        check_frame.pack(side=LEFT, padx=(20,0))
        self.include_hidden_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(check_frame, text="隠しファイル", variable=self.include_hidden_var, bootstyle="round-toggle").pack(side=LEFT, padx=10)
        self.case_sensitive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(check_frame, text="大文字/小文字を区別", variable=self.case_sensitive_var, bootstyle="round-toggle").pack(side=LEFT, padx=10)

    def create_results_widgets(self, parent):
        result_frame = ttk.Frame(parent)
        result_frame.pack(fill=BOTH, expand=True)
        x_scrollbar = ttk.Scrollbar(result_frame, orient=HORIZONTAL, bootstyle="round")
        x_scrollbar.pack(side=BOTTOM, fill=X)
        y_scrollbar = ttk.Scrollbar(result_frame, orient=VERTICAL, bootstyle="round")
        y_scrollbar.pack(side=RIGHT, fill=Y)
        self.result_listbox = tk.Listbox(result_frame, xscrollcommand=x_scrollbar.set, yscrollcommand=y_scrollbar.set)
        self.result_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        x_scrollbar.config(command=self.result_listbox.xview)
        y_scrollbar.config(command=self.result_listbox.yview)
        self.result_listbox.bind("<Double-Button-1>", self.open_selected_path)
        self.result_listbox.bind("<Button-3>", self.show_context_menu)

    def create_statusbar(self):
        status_frame = ttk.Frame(self, padding=(5, 2))
        status_frame.pack(side=BOTTOM, fill=X)
        self.status_var = tk.StringVar(value="フォルダとキーワードを入力してください")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.pack(side=LEFT)
        right_frame = ttk.Frame(status_frame)
        right_frame.pack(side=RIGHT)
        self.time_var = tk.StringVar()
        self.time_label = ttk.Label(right_frame, textvariable=self.time_var)
        self.time_label.pack(side=RIGHT, padx=(5,0))
        self.found_count_var = tk.StringVar()
        self.found_count_label = ttk.Label(right_frame, textvariable=self.found_count_var)
        self.found_count_label.pack(side=RIGHT)

    def create_menu(self):
        menubar = ttk.Menu(self)
        self.config(menu=menubar)
        theme_menu = ttk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="テーマ切替", menu=theme_menu)
        for theme in self.style.theme_names():
            theme_menu.add_radiobutton(label=theme, command=lambda t=theme: self.change_theme(t))

    def change_theme(self, theme_name: str):
        self.style.theme_use(theme_name)
        select_bg = self.style.colors.selectbg
        self.result_listbox.config(selectbackground=select_bg)

    def start_search(self, event=None):
        if self.search_button["state"] == "disabled": return
        self.search_button.config(state=DISABLED, text="検索中...")
        self.status_var.set("🔍 検索中...")
        self.found_count_var.set("")
        self.time_var.set("")
        self.result_listbox.delete(0, "end")
        self.update_idletasks()
        self.results_queue.clear()
        self.found_count = 0
        self.search_start_time = time.time()
        threading.Thread(target=self.run_fd_search, daemon=True).start()
        self.periodic_gui_updater()

    def run_fd_search(self):
        folder = self.folder_var.get()
        keyword = self.keyword_var.get().strip()
        fd_path = resource_path("fd.exe") if platform.system() == "Windows" else "fd"
        if not os.path.isdir(folder):
            self.results_queue.append(("error", "検索フォルダが存在しません。"))
            return
        if not keyword:
            self.results_queue.append(("error", "検索キーワードを入力してください。"))
            return
        if platform.system() == "Windows" and not os.path.isfile(fd_path):
            self.results_queue.append(("error", f"'{os.path.basename(fd_path)}' が見つかりません。"))
            return
        cmd = [fd_path, keyword, folder, "--absolute-path"]
        if self.type_var.get() in ("f", "d"): cmd += ["-t", self.type_var.get()]
        if self.include_hidden_var.get(): cmd.append("--hidden")
        cmd.append("--case-sensitive" if self.case_sensitive_var.get() else "--ignore-case")
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            self.search_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors='ignore', creationflags=creation_flags
            )
            for line in iter(self.search_process.stdout.readline, ''):
                path = line.strip()
                if path:
                    self.results_queue.append(("path", path))
            self.search_process.wait()
            stderr_output = self.search_process.stderr.read()
            if self.search_process.returncode not in (0, 1) and stderr_output:
                 self.results_queue.append(("error", f"fd 実行エラー:\n{stderr_output}"))
        except FileNotFoundError:
             self.results_queue.append(("error", f"'{os.path.basename(fd_path)}' が見つかりません。"))
        except Exception as e:
            self.results_queue.append(("error", f"予期せぬエラーが発生しました: {e}"))
        finally:
            self.results_queue.append(("done", None))
            self.search_process = None

    def periodic_gui_updater(self):
        items_to_add = []
        is_done = False
        error_msg = None
        while self.results_queue:
            msg_type, data = self.results_queue.popleft()
            if msg_type == "path":
                items_to_add.append(data)
            elif msg_type == "error":
                error_msg = data
                is_done = True
                break
            elif msg_type == "done":
                is_done = True
                break
        if items_to_add:
            for item in items_to_add:
                self.result_listbox.insert("end", item)
            self.found_count += len(items_to_add)
            self.found_count_var.set(f"{self.found_count} 件")
        if error_msg:
            self.show_error(error_msg)
            return
        if is_done:
            self.finalize_search()
            return
        self.update_job = self.after(300, self.periodic_gui_updater)

    def finalize_search(self):
        elapsed_time = time.time() - self.search_start_time
        if self.found_count == 0:
            self.result_listbox.insert("end", "一致するファイルは見つかりませんでした。")
            self.status_var.set("✅ 検索完了")
        else:
            self.status_var.set("✅ 検索完了")
        self.found_count_var.set(f"{self.found_count} 件")
        self.time_var.set(f"({elapsed_time:.2f}秒)")
        self.on_keyword_change()
        self.search_button.config(text="検索開始")
        self.change_theme(self.style.theme.name)

    def show_error(self, msg: str):
        messagebox.showerror("エラー", msg)
        self.status_var.set("❌ エラーが発生しました")
        self.found_count_var.set("")
        self.time_var.set("")
        self.on_keyword_change()
        self.search_button.config(text="検索開始")

    def on_keyword_change(self, *args):
        folder_exists = self.folder_var.get()
        keyword_exists = self.keyword_var.get().strip()
        if folder_exists and keyword_exists:
            self.search_button.config(state=NORMAL)
        else:
            self.search_button.config(state=DISABLED)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)
            self.on_keyword_change()

    def show_context_menu(self, event):
        selection_idx = self.result_listbox.nearest(event.y)
        if not self.result_listbox.selection_includes(selection_idx):
            self.result_listbox.selection_clear(0, 'end')
            self.result_listbox.selection_set(selection_idx)
            self.result_listbox.activate(selection_idx)
        if self.result_listbox.curselection():
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

    def open_file_location(self):
        """選択したファイルの格納場所をOSのファイルエクスプローラーで開く。"""
        selection = self.result_listbox.curselection()
        if not selection: return
        path = self.result_listbox.get(selection[0])
        if not os.path.exists(path):
            messagebox.showwarning("警告", "選択されたパスは存在しません。"); return
        try:
            if platform.system() == "Windows":
                subprocess.run(['explorer', '/select,', os.path.normpath(path)])
            elif platform.system() == "Darwin": # macOS
                subprocess.run(['open', '-R', path])
            else: # Linux
                dir_path = os.path.dirname(path) if os.path.isfile(path) else path
                subprocess.run(['xdg-open', dir_path])
        except Exception as e:
            messagebox.showerror("エラー", f"場所を開けませんでした: {e}")

    def copy_path_to_clipboard(self):
        selection = self.result_listbox.curselection()
        if not selection: return
        path = self.result_listbox.get(selection[0])
        self.clipboard_clear()
        self.clipboard_append(path)
        self.status_var.set(f"📋 パスをコピーしました: {path}")

    def open_selected_path(self, event=None):
        """選択したアイテムをOSのデフォルトアプリケーションで開く（ダブルクリック時の動作）。"""
        selection = self.result_listbox.curselection()
        if not selection: return
        path = self.result_listbox.get(selection[0])
        if not os.path.exists(path):
            messagebox.showwarning("警告", "選択されたパスは存在しません。"); return
        try:
            if platform.system() == "Windows":
                os.startfile(os.path.normpath(path))
            else:
                 subprocess.run(['open' if platform.system() == "Darwin" else 'xdg-open', path])
        except Exception as e:
            messagebox.showerror("エラー", f"ファイル/フォルダを開けませんでした: {e}")

if __name__ == "__main__":
    # ★ 変更: コンストラクタからテーマ指定を削除。設定ファイルから読み込むため。
    app = FdSearchApp()
    app.mainloop()