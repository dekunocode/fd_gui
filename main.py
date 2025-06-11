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
import json
from collections import deque
from datetime import datetime

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

    def __init__(self):
        self.settings_file = resource_path('settings.json')
        self.history_dir = resource_path('history')
        settings = self.load_settings()
        initial_theme = settings.get('theme', 'superhero')

        super().__init__(themename=initial_theme)
        self.title("fd ファイル検索ツール")
        self.geometry("800x750")

        # --- インスタンス変数 ---
        self.search_process = None
        self.results_queue = deque()
        self.update_job = None
        self.found_count = 0
        self.all_results = []
        self.displayed_results = []

        # --- ウィジェットの作成 ---
        self.set_icon()
        self.create_context_menu()
        self.create_widgets()

        # --- 設定の適用と終了処理 ---
        self.apply_settings(settings)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_settings(self) -> dict:
        if not os.path.exists(self.settings_file):
            return {}
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"設定ファイルを読み込めませんでした: {e}")
            return {}

    def save_settings(self):
        settings_data = {
            'theme': self.style.theme.name,
            'folder': self.folder_var.get(),
            'hidden': self.include_hidden_var.get(),
            'case_sensitive': self.case_sensitive_var.get(),
            'type': self.type_var.get(),
        }
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"設定ファイルを保存できませんでした: {e}")

    def apply_settings(self, settings: dict):
        self.folder_var.set(settings.get('folder', ''))
        self.include_hidden_var.set(settings.get('hidden', False))
        self.case_sensitive_var.set(settings.get('case_sensitive', False))
        self.type_var.set(settings.get('type', 'all'))
        self.on_keyword_change()

    def on_closing(self):
        self.save_settings()
        self.destroy()

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

    def create_menu(self):
        menubar = ttk.Menu(self)
        self.config(menu=menubar)

        # ★ ファイルメニューを追加
        file_menu = ttk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="終了", command=self.on_closing)
        menubar.add_cascade(label="ファイル", menu=file_menu)

        self.history_menu = ttk.Menu(menubar, tearoff=False)
        self.history_menu.add_command(label="現在の検索結果を保存", command=self.save_history, state="disabled")
        self.history_menu.add_command(label="履歴ファイルを開く", command=self.load_history)
        menubar.add_cascade(label="履歴", menu=self.history_menu)

        theme_menu = ttk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="テーマ切替", menu=theme_menu)
        for theme in self.style.theme_names():
            theme_menu.add_radiobutton(label=theme, command=lambda t=theme: self.change_theme(t))

    def save_history(self):
        if not self.all_results:
            messagebox.showinfo("情報", "保存する検索結果がありません。")
            return

        history_data = {
            "saved_at": datetime.now().isoformat(),
            "search_folder": self.folder_var.get(),
            "keyword": self.keyword_var.get(),
            "options": {
                "type": self.type_var.get(),
                "hidden": self.include_hidden_var.get(),
                "case_sensitive": self.case_sensitive_var.get(),
            },
            "results": self.all_results
        }

        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)

        filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"
        filepath = os.path.join(self.history_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=4, ensure_ascii=False)
            self.status_var.set(f"✅ 履歴を保存しました: {filename}")
        except Exception as e:
            messagebox.showerror("エラー", f"履歴の保存に失敗しました: {e}")

    def load_history(self):
        filepath = filedialog.askopenfilename(
            title="履歴ファイルを開く",
            initialdir=self.history_dir,
            filetypes=[("JSONファイル", "*.json")]
        )
        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                history_data = json.load(f)

            self.folder_var.set(history_data.get("search_folder", ""))
            self.keyword_var.set(history_data.get("keyword", ""))

            options = history_data.get("options", {})
            self.type_var.set(options.get("type", "all"))
            self.include_hidden_var.set(options.get("hidden", False))
            self.case_sensitive_var.set(options.get("case_sensitive", False))

            self.all_results = history_data.get("results", [])
            self.displayed_results = self.all_results[:]

            self.result_listbox.delete(0, "end")
            relative_paths = [item[1] for item in self.all_results]
            self.result_listbox.insert("end", *relative_paths)

            self.found_count = len(self.all_results)
            self.found_count_var.set(f"{self.found_count} 件")
            self.time_var.set(f"(履歴: {os.path.basename(filepath)})")

            self.status_var.set(f"✅ 履歴を読み込みました (Enterで結果を絞り込めます)")
            self.filter_entry.focus_set()
            self.history_menu.entryconfig("現在の検索結果を保存", state="normal")

        except Exception as e:
            messagebox.showerror("エラー", f"履歴の読み込みに失敗しました: {e}")

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
        result_frame = ttk.LabelFrame(parent, text="検索結果", padding=10)
        result_frame.pack(fill=BOTH, expand=True)

        filter_frame = ttk.Frame(result_frame)
        filter_frame.pack(fill=X, pady=(0, 5))
        ttk.Label(filter_frame, text="あいまい検索で絞り込み:").pack(side=LEFT, padx=(0,5))
        self.filter_var = tk.StringVar()
        self.filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var)
        self.filter_entry.pack(fill=X, expand=True)
        self.filter_entry.bind("<Return>", self.filter_results)

        list_frame = ttk.Frame(result_frame)
        list_frame.pack(fill=BOTH, expand=True)
        x_scrollbar = ttk.Scrollbar(list_frame, orient=HORIZONTAL, bootstyle="round")
        x_scrollbar.pack(side=BOTTOM, fill=X)
        y_scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, bootstyle="round")
        y_scrollbar.pack(side=RIGHT, fill=Y)
        self.result_listbox = tk.Listbox(list_frame, xscrollcommand=x_scrollbar.set, yscrollcommand=y_scrollbar.set)
        self.result_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        x_scrollbar.config(command=self.result_listbox.xview)
        y_scrollbar.config(command=self.result_listbox.yview)
        self.result_listbox.bind("<Double-Button-1>", self.open_selected_path)
        self.result_listbox.bind("<Button-3>", self.show_context_menu)

    def get_selected_absolute_path(self) -> str | None:
        selection_indices = self.result_listbox.curselection()
        if not selection_indices:
            return None
        selected_index = selection_indices[0]
        if selected_index < len(self.displayed_results):
            return self.displayed_results[selected_index][0]
        return None

    def fuzzy_match(self, query: str, target: str) -> bool:
        query = query.lower()
        target = target.lower()
        query_idx = 0
        target_idx = 0
        while query_idx < len(query) and target_idx < len(target):
            if query[query_idx] == target[target_idx]:
                query_idx += 1
            target_idx += 1
        return query_idx == len(query)

    def filter_results(self, event=None):
        query = self.filter_var.get()
        self.result_listbox.delete(0, "end")

        if not query:
            self.displayed_results = self.all_results[:]
        else:
            self.displayed_results = [item for item in self.all_results if self.fuzzy_match(query, item[1])]

        if not self.displayed_results:
            self.result_listbox.insert("end", "（検索結果なし）")
            self.status_var.set(f"✅ 絞り込みの結果、0件です")
        else:
            relative_paths = [item[1] for item in self.displayed_results]
            self.result_listbox.insert("end", *relative_paths)
            if not query:
                 self.status_var.set(f"✅ 全 {len(self.all_results)} 件を表示中 (Enterで絞り込み)")
            else:
                 self.status_var.set(f"✅ {len(self.displayed_results)} 件に絞り込みました (Enterで再度絞り込み)")

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

    def change_theme(self, theme_name: str):
        self.style.theme_use(theme_name)
        select_bg = self.style.colors.selectbg
        self.result_listbox.config(selectbackground=select_bg)

    def start_search(self, event=None):
        if self.search_button["state"] == "disabled": return

        if not os.path.isdir(self.folder_var.get()):
            messagebox.showerror("エラー", "指定された検索フォルダは存在しません。")
            return

        self.history_menu.entryconfig("現在の検索結果を保存", state="disabled")
        self.search_button.config(state=DISABLED, text="検索中...")
        self.status_var.set("🔍 検索中...")
        self.found_count_var.set("")
        self.time_var.set("")

        self.result_listbox.delete(0, "end")
        self.filter_var.set("")
        self.all_results.clear()
        self.displayed_results.clear()

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
                abs_path = line.strip()
                if abs_path:
                    rel_path = os.path.relpath(abs_path, folder)
                    self.results_queue.append(("path", (abs_path, rel_path)))
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
            relative_paths = [item[1] for item in items_to_add]
            self.result_listbox.insert("end", *relative_paths)
            self.all_results.extend(items_to_add)
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
        self.displayed_results = self.all_results[:]
        elapsed_time = time.time() - self.search_start_time
        if self.found_count == 0:
            self.result_listbox.insert("end", "一致するファイルは見つかりませんでした。")
            self.status_var.set("✅ 検索完了")
            self.history_menu.entryconfig("現在の検索結果を保存", state="disabled")
        else:
            self.status_var.set(f"✅ 検索完了 (Enterで結果を絞り込めます)")
            self.history_menu.entryconfig("現在の検索結果を保存", state="normal")

        self.found_count_var.set(f"{self.found_count} 件")
        self.time_var.set(f"({elapsed_time:.2f}秒)")
        self.on_keyword_change()
        self.search_button.config(text="検索開始")
        self.change_theme(self.style.theme.name)
        if self.found_count > 0:
             self.filter_entry.focus_set()

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
        if self.result_listbox.size() == 0 or self.result_listbox.get(0).startswith("（"): return
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
        path = self.get_selected_absolute_path()
        if not path: return
        if not os.path.exists(path):
            messagebox.showwarning("警告", "選択されたパスは存在しません。"); return
        try:
            if platform.system() == "Windows":
                subprocess.run(['explorer', '/select,', os.path.normpath(path)])
            elif platform.system() == "Darwin":
                subprocess.run(['open', '-R', path])
            else:
                dir_path = os.path.dirname(path) if os.path.isfile(path) else path
                subprocess.run(['xdg-open', dir_path])
        except Exception as e:
            messagebox.showerror("エラー", f"場所を開けませんでした: {e}")

    def copy_path_to_clipboard(self):
        path = self.get_selected_absolute_path()
        if not path: return
        self.clipboard_clear()
        self.clipboard_append(path)
        self.status_var.set(f"📋 パスをコピーしました: {path}")

    def open_selected_path(self, event=None):
        path = self.get_selected_absolute_path()
        if not path: return
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
    app = FdSearchApp()
    app.mainloop()