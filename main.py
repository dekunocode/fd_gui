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

# --- Language translations ---
translations = {
    'en': {
        'title': 'fd File Search Tool',
        'search_folder': 'Search Folder:',
        'browse': 'Browse',
        'search_keyword': 'Search Keyword:',
        'search_options': 'Search Options',
        'all': 'All',
        'file_only': 'Files Only',
        'dir_only': 'Directories Only',
        'hidden': 'Hidden Files',
        'case_sensitive': 'Case Sensitive',
        'start_search': 'Start Search',
        'search_results': 'Search Results',
        'fuzzy_filter': 'Fuzzy Filter:',
        'status_ready': 'Please enter folder and keyword',
        'status_searching': '🔍 Searching...',
        'status_done': '✅ Search complete',
        'status_no_results': 'No matching files found.',
        'context_open': 'Open location in Explorer',
        'context_copy': 'Copy path',
        'menu_file': 'File',
        'menu_exit': 'Exit',
        'menu_history': 'History',
        'menu_save_history': 'Save current search results',
        'menu_open_history': 'Open history file',
        'menu_theme': 'Theme',
        'menu_language': 'Language',
        'lang_en': 'English',
        'lang_ja': '日本語',
    },
    'ja': {
        'title': 'fd ファイル検索ツール',
        'search_folder': '検索フォルダ:',
        'browse': '参照',
        'search_keyword': '検索キーワード:',
        'search_options': '検索オプション',
        'all': 'すべて',
        'file_only': 'ファイルのみ',
        'dir_only': 'ディレクトリのみ',
        'hidden': '隠しファイル',
        'case_sensitive': '大文字/小文字を区別',
        'start_search': '検索開始',
        'search_results': '検索結果',
        'fuzzy_filter': 'あいまい検索で絞り込み:',
        'status_ready': 'フォルダとキーワードを入力してください',
        'status_searching': '🔍 検索中...',
        'status_done': '✅ 検索完了',
        'status_no_results': '一致するファイルは見つかりませんでした。',
        'context_open': 'この場所をエクスプローラーで開く',
        'context_copy': 'パスをコピー',
        'menu_file': 'ファイル',
        'menu_exit': '終了',
        'menu_history': '履歴',
        'menu_save_history': '現在の検索結果を保存',
        'menu_open_history': '履歴ファイルを開く',
        'menu_theme': 'テーマ切替',
        'menu_language': '言語',
        'lang_en': 'English',
        'lang_ja': '日本語',
    }
}

# Utility function to resolve resource file paths depending on the execution environment.
def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class FdSearchApp(ttk.Window):
    """Main window class for the fd command GUI wrapper application."""

    def __init__(self):
        self.language = 'en'  # Default language
        self.settings_file = resource_path('settings.json')
        self.history_dir = resource_path('history')
        settings = self.load_settings()
        initial_theme = settings.get('theme', 'superhero')

        super().__init__(themename=initial_theme)
        self.title(translations[self.language]['title'])
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
        """Load application settings from the settings file (JSON)."""
        if not os.path.exists(self.settings_file):
            return {}
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Could not load settings file: {e}")
            return {}

    def save_settings(self):
        """Save current application settings to the settings file (JSON)."""
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
            print(f"Could not save settings file: {e}")

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
        """Set the application icon if available."""
        icon_path = resource_path('icon/icon.ico')
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                print(f"Could not set icon: {e}")

    def create_context_menu(self):
        """Create the right-click context menu for result list."""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label=translations[self.language]['context_open'], command=self.open_file_location)
        self.context_menu.add_command(label=translations[self.language]['context_copy'], command=self.copy_path_to_clipboard)

    def create_widgets(self):
        self.create_menu()
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=BOTH, expand=True)
        self.create_settings_widgets(main_frame)
        self.create_options_widgets(main_frame)
        self.search_button = ttk.Button(main_frame, text=translations[self.language]['start_search'], command=self.start_search, bootstyle=(SUCCESS, OUTLINE))
        self.search_button.pack(fill=X, pady=10, ipady=5)
        self.search_button.config(state=DISABLED)
        self.create_results_widgets(main_frame)
        self.create_statusbar()

    def create_menu(self):
        """Create the application menu bar."""
        menubar = ttk.Menu(self)
        self.config(menu=menubar)

        file_menu = ttk.Menu(menubar, tearoff=False)
        file_menu.add_command(label=translations[self.language]['menu_exit'], command=self.on_closing)
        menubar.add_cascade(label=translations[self.language]['menu_file'], menu=file_menu)

        self.history_menu = ttk.Menu(menubar, tearoff=False)
        self.history_menu.add_command(label=translations[self.language]['menu_save_history'], command=self.save_history, state="disabled")
        self.save_history_index = 0  # Save the index for later reference
        self.history_menu.add_command(label=translations[self.language]['menu_open_history'], command=self.load_history)
        menubar.add_cascade(label=translations[self.language]['menu_history'], menu=self.history_menu)

        theme_menu = ttk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label=translations[self.language]['menu_theme'], menu=theme_menu)
        for theme in self.style.theme_names():
            theme_menu.add_radiobutton(label=theme, command=lambda t=theme: self.change_theme(t))

        # Language menu
        lang_menu = ttk.Menu(menubar, tearoff=False)
        lang_menu.add_radiobutton(label=translations['en']['lang_en'], command=lambda: self.set_language('en'))
        lang_menu.add_radiobutton(label=translations['ja']['lang_ja'], command=lambda: self.set_language('ja'))
        menubar.add_cascade(label=translations[self.language]['menu_language'], menu=lang_menu)

    def set_language(self, lang):
        if lang not in translations:
            return
        self.language = lang
        self.update_language()

    def update_language(self):
        # --- Save current entry values ---
        folder_value = self.folder_var.get() if hasattr(self, 'folder_var') else ''
        keyword_value = self.keyword_var.get() if hasattr(self, 'keyword_var') else ''
        # Update window title and all widget labels
        self.title(translations[self.language]['title'])
        # Re-create all widgets and menus
        for widget in self.winfo_children():
            widget.destroy()
        self.create_context_menu()
        self.create_widgets()
        # --- Restore entry values ---
        if hasattr(self, 'folder_var'):
            self.folder_var.set(folder_value)
        if hasattr(self, 'keyword_var'):
            self.keyword_var.set(keyword_value)

    def save_history(self):
        """Save the current search results to a history file (JSON)."""
        if not self.all_results:
            messagebox.showinfo("Info", "No search results to save.")
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
            self.status_var.set(f"✅ History saved: {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save history: {e}")

    def load_history(self):
        """Load search results from a history file (JSON)."""
        filepath = filedialog.askopenfilename(
            title=translations[self.language]['menu_open_history'],
            initialdir=self.history_dir,
            filetypes=[("JSON files", "*.json")]
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
            self.found_count_var.set(f"{self.found_count} items")
            self.time_var.set(f"(History: {os.path.basename(filepath)})")

            self.status_var.set(f"✅ History loaded (Press Enter to filter results)")
            self.filter_entry.focus_set()
            self.history_menu.entryconfig(self.save_history_index, state="normal")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load history: {e}")

    def create_settings_widgets(self, parent):
        settings_frame = ttk.Frame(parent)
        settings_frame.pack(fill=X, pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        ttk.Label(settings_frame, text=translations[self.language]['search_folder']).grid(row=0, column=0, padx=(0, 5), sticky=W)
        self.folder_var = tk.StringVar()
        folder_entry = ttk.Entry(settings_frame, textvariable=self.folder_var)
        folder_entry.grid(row=0, column=1, sticky=EW, padx=(0, 5))
        ttk.Button(settings_frame, text=translations[self.language]['browse'], command=self.browse_folder, bootstyle=SECONDARY).grid(row=0, column=2)
        ttk.Label(settings_frame, text=translations[self.language]['search_keyword']).grid(row=1, column=0, padx=(0, 5), pady=(5,0), sticky=W)
        self.keyword_var = tk.StringVar()
        self.keyword_var.trace_add("write", self.on_keyword_change)
        keyword_entry = ttk.Entry(settings_frame, textvariable=self.keyword_var)
        keyword_entry.grid(row=1, column=1, columnspan=2, sticky=EW, pady=(5,0))
        keyword_entry.bind("<Return>", self.start_search)

    def create_options_widgets(self, parent):
        options_frame = ttk.LabelFrame(parent, text=translations[self.language]['search_options'], padding=10)
        options_frame.pack(fill=X, pady=5)
        type_frame = ttk.Frame(options_frame)
        type_frame.pack(side=LEFT, fill=X, expand=True)
        self.type_var = tk.StringVar(value="all")
        ttk.Radiobutton(type_frame, text=translations[self.language]['all'], value="all", variable=self.type_var, bootstyle="outline-toolbutton").pack(side=LEFT, padx=(0,5), expand=True, fill=X)
        ttk.Radiobutton(type_frame, text=translations[self.language]['file_only'], value="f", variable=self.type_var, bootstyle="outline-toolbutton").pack(side=LEFT, padx=5, expand=True, fill=X)
        ttk.Radiobutton(type_frame, text=translations[self.language]['dir_only'], value="d", variable=self.type_var, bootstyle="outline-toolbutton").pack(side=LEFT, padx=5, expand=True, fill=X)
        check_frame = ttk.Frame(options_frame)
        check_frame.pack(side=LEFT, padx=(20,0))
        self.include_hidden_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(check_frame, text=translations[self.language]['hidden'], variable=self.include_hidden_var, bootstyle="round-toggle").pack(side=LEFT, padx=10)
        self.case_sensitive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(check_frame, text=translations[self.language]['case_sensitive'], variable=self.case_sensitive_var, bootstyle="round-toggle").pack(side=LEFT, padx=10)

    def create_results_widgets(self, parent):
        result_frame = ttk.LabelFrame(parent, text=translations[self.language]['search_results'], padding=10)
        result_frame.pack(fill=BOTH, expand=True)

        filter_frame = ttk.Frame(result_frame)
        filter_frame.pack(fill=X, pady=(0, 5))
        ttk.Label(filter_frame, text=translations[self.language]['fuzzy_filter']).pack(side=LEFT, padx=(0,5))
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
            self.result_listbox.insert("end", translations[self.language]['status_no_results'])
            self.status_var.set(f"{translations[self.language]['status_done']} 0")
        else:
            relative_paths = [item[1] for item in self.displayed_results]
            self.result_listbox.insert("end", *relative_paths)
            if not query:
                self.status_var.set(f"{translations[self.language]['status_done']} {len(self.all_results)}")
            else:
                self.status_var.set(f"{translations[self.language]['status_done']} {len(self.displayed_results)}")

    def create_statusbar(self):
        status_frame = ttk.Frame(self, padding=(5, 2))
        status_frame.pack(side=BOTTOM, fill=X)
        self.status_var = tk.StringVar(value=translations[self.language]['status_ready'])
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

    def change_language(self, lang_code: str):
        if lang_code not in translations:
            return
        for key, value in translations[lang_code].items():
            if hasattr(self, key):
                getattr(self, key).set(value)
        self.apply_settings(self.load_settings())

    def start_search(self, event=None):
        if self.search_button["state"] == "disabled": return

        if not os.path.isdir(self.folder_var.get()):
            messagebox.showerror("エラー", "指定された検索フォルダは存在しません。")
            return

        self.history_menu.entryconfig(self.save_history_index, state="disabled")
        self.search_button.config(state=DISABLED, text=translations[self.language]['status_searching'])
        self.status_var.set(translations[self.language]['status_searching'])
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
            self.displayed_results.extend(items_to_add) # ★ 修正: displayed_resultsもリアルタイムで更新
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
            self.result_listbox.insert("end", translations[self.language]['status_no_results'])
            self.status_var.set(translations[self.language]['status_done'])
            self.history_menu.entryconfig(self.save_history_index, state="disabled")
        else:
            self.status_var.set(f"{translations[self.language]['status_done']} (Enterで結果を絞り込めます)")
            self.history_menu.entryconfig(self.save_history_index, state="normal")

        self.found_count_var.set(f"{self.found_count} 件")
        self.time_var.set(f"({elapsed_time:.2f}秒)")
        self.on_keyword_change()
        self.search_button.config(text=translations[self.language]['start_search'])
        self.change_theme(self.style.theme.name)
        if self.found_count > 0:
             self.filter_entry.focus_set()

    def show_error(self, msg: str):
        messagebox.showerror("エラー", msg)
        self.status_var.set("❌ エラーが発生しました")
        self.found_count_var.set("")
        self.time_var.set("")
        self.on_keyword_change()
        self.search_button.config(text=translations[self.language]['start_search'])

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