import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import subprocess
import threading
import os
import platform
import sys

def resource_path(relative_path: str) -> str:
    """
    実行環境（スクリプト or cx_Freeze/PyInstallerによるexe）に応じて、
    リソースファイルへの絶対パスを解決して返す。

    Args:
        relative_path (str): スクリプトからの相対パス。

    Returns:
        str: リソースファイルへの絶対パス。
    """
    try:
        # cx_FreezeやPyInstallerは、実行時に一時フォルダを作成し、
        # そこにリソースを展開する。その一時フォルダのパスを取得する。
        base_path = sys._MEIPASS
    except AttributeError:
        # 開発環境（通常のスクリプト実行）では、
        # スクリプトファイルが存在するディレクトリを基準とする。
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class FdSearchApp(ttk.Window):
    """fdコマンドのGUIラッパーアプリケーションのメインウィンドウクラス。"""

    def __init__(self, themename: str = 'superhero'):
        """
        ウィンドウを初期化し、ウィジェットを作成する。

        Args:
            themename (str, optional): 初期状態で適用するttkbootstrapのテーマ名。
                                      Defaults to 'superhero'.
        """
        super().__init__(themename=themename)
        self.title("fd ファイル検索ツール")
        self.geometry("800x630")

        # --- 初期設定 ---
        self.set_icon()
        self.create_context_menu()
        self.create_widgets()

    def set_icon(self):
        """ウィンドウアイコンを設定する。"""
        # resource_path関数で、実行環境に応じたアイコンへの絶対パスを取得
        icon_path = resource_path('icon/icon.ico')
        if os.path.exists(icon_path):
            try:
                # ご指摘に基づき、引数のキーワードを削除して修正
                self.iconbitmap(icon_path)
            except Exception as e:
                # アイコン設定に失敗してもアプリは継続させる
                print(f"アイコンを設定できませんでした: {e}")

    def create_context_menu(self):
        """検索結果リストボックスの右クリックメニューを作成する。"""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(
            label="この場所をエクスプローラーで開く",
            command=self.open_file_location
        )
        self.context_menu.add_command(
            label="パスをコピー",
            command=self.copy_path_to_clipboard
        )

    def create_widgets(self):
        """アプリケーションの全ウィジェットを作成・配置する。"""
        # --- メニューバー ---
        self.create_menu()

        # --- メインフレーム (全ウィジェットの親) ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=BOTH, expand=True)

        # --- 検索設定フレーム (フォルダとキーワード) ---
        self.create_settings_widgets(main_frame)

        # --- オプションフレーム (種別や検索条件) ---
        self.create_options_widgets(main_frame)

        # --- 検索ボタン ---
        self.search_button = ttk.Button(
            main_frame,
            text="検索開始",
            command=self.start_search,
            bootstyle=(SUCCESS, OUTLINE)
        )
        self.search_button.pack(fill=X, pady=10, ipady=5)
        self.search_button.config(state=DISABLED) # 初期状態は無効

        # --- 結果表示フレーム (リストとスクロールバー) ---
        self.create_results_widgets(main_frame)

        # --- ステータスバー ---
        self.create_statusbar()

    def create_settings_widgets(self, parent):
        """検索フォルダとキーワード入力欄を作成する。"""
        settings_frame = ttk.Frame(parent)
        settings_frame.pack(fill=X, pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1) # 2列目のEntryを伸縮させる

        ttk.Label(settings_frame, text="検索フォルダ:").grid(row=0, column=0, padx=(0, 5), sticky=W)
        self.folder_var = tk.StringVar()
        folder_entry = ttk.Entry(settings_frame, textvariable=self.folder_var)
        folder_entry.grid(row=0, column=1, sticky=EW, padx=(0, 5))
        ttk.Button(settings_frame, text="参照", command=self.browse_folder, bootstyle=SECONDARY).grid(row=0, column=2)

        ttk.Label(settings_frame, text="検索キーワード:").grid(row=1, column=0, padx=(0, 5), pady=(5,0), sticky=W)
        self.keyword_var = tk.StringVar()
        self.keyword_var.trace_add("write", self.on_keyword_change) # 入力を監視し、ボタンの状態を更新
        keyword_entry = ttk.Entry(settings_frame, textvariable=self.keyword_var)
        keyword_entry.grid(row=1, column=1, columnspan=2, sticky=EW, pady=(5,0))
        keyword_entry.bind("<Return>", self.start_search) # Enterキーでも検索実行

    def create_options_widgets(self, parent):
        """ファイル種別や検索オプションのウィジェットを作成する。"""
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
        """検索結果を表示するリストボックスとスクロールバーを作成する。"""
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

        # イベントのバインド
        self.result_listbox.bind("<Double-Button-1>", self.open_selected_path)
        self.result_listbox.bind("<Button-3>", self.show_context_menu)

    def create_statusbar(self):
        """アプリケーションの状態を表示するステータスバーを作成する。"""
        status_frame = ttk.Frame(self, padding=(5, 2))
        status_frame.pack(side=BOTTOM, fill=X)
        self.status_var = tk.StringVar(value="フォルダとキーワードを入力してください")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.pack(side=LEFT)

    def create_menu(self):
        """テーマ切り替え機能を持つメニューバーを作成する。"""
        menubar = ttk.Menu(self)
        self.config(menu=menubar)
        theme_menu = ttk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="テーマ切替", menu=theme_menu)
        for theme in self.style.theme_names():
            theme_menu.add_radiobutton(label=theme, command=lambda t=theme: self.change_theme(t))

    def change_theme(self, theme_name: str):
        """アプリケーションのテーマを動的に変更する。"""
        self.style.theme_use(theme_name)
        # テーマ変更時にListboxの選択色も追従させる
        select_bg = self.style.colors.selectbg
        self.result_listbox.config(selectbackground=select_bg)

    def show_context_menu(self, event):
        """右クリックされた位置にコンテキストメニューを表示する。"""
        # クリックされたアイテムを選択状態にする
        selection_idx = self.result_listbox.nearest(event.y)
        if not self.result_listbox.selection_includes(selection_idx):
            self.result_listbox.selection_clear(0, 'end')
            self.result_listbox.selection_set(selection_idx)
            self.result_listbox.activate(selection_idx)

        # 選択アイテムがある場合のみメニューを表示
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
                # /select, オプションでファイルを選択した状態でフォルダを開く
                subprocess.run(['explorer', '/select,', os.path.normpath(path)], check=True)
            elif platform.system() == "Darwin": # macOS
                # -R オプションでFinderにファイルを表示
                subprocess.run(['open', '-R', path], check=True)
            else: # Linux
                # ファイルなら親ディレクトリを、ディレクトリならそのものを開く
                dir_path = os.path.dirname(path) if os.path.isfile(path) else path
                subprocess.run(['xdg-open', dir_path], check=True)
        except Exception as e:
            messagebox.showerror("エラー", f"場所を開けませんでした: {e}")

    def copy_path_to_clipboard(self):
        """選択したアイテムのフルパスをクリップボードにコピーする。"""
        selection = self.result_listbox.curselection()
        if not selection: return

        path = self.result_listbox.get(selection[0])
        self.clipboard_clear()
        self.clipboard_append(path)
        self.status_var.set(f"📋 パスをコピーしました: {path}")

    def on_keyword_change(self, *args):
        """入力に応じて検索ボタンの有効/無効を切り替える。"""
        folder_exists = self.folder_var.get()
        keyword_exists = self.keyword_var.get().strip()
        if folder_exists and keyword_exists:
            self.search_button.config(state=NORMAL)
        else:
            self.search_button.config(state=DISABLED)

    def browse_folder(self):
        """「参照」ボタンの動作。フォルダ選択ダイアログを開く。"""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)
            self.on_keyword_change()

    def start_search(self, event=None):
        """検索処理をバックグラウンドスレッドで開始する。"""
        if self.search_button["state"] == "disabled": return

        # UIを検索中状態に更新
        self.search_button.config(state=DISABLED, text="検索中...")
        self.status_var.set("🔍 検索中...")
        self.update_idletasks()
        self.result_listbox.delete(0, "end")

        # UIが固まらないように別スレッドで重い処理を実行
        threading.Thread(target=self.run_fd_search, daemon=True).start()

    def run_fd_search(self):
        """fdコマンドを構築し、サブプロセスとして実行する。"""
        folder = self.folder_var.get()
        keyword = self.keyword_var.get().strip()
        fd_path = resource_path("fd.exe") if platform.system() == "Windows" else "fd"

        # --- 検索前のバリデーション ---
        if not os.path.isdir(folder): self.show_error("検索フォルダが存在しません。"); return
        if not keyword: self.show_error("検索キーワードを入力してください。"); return
        if platform.system() == "Windows" and not os.path.isfile(fd_path):
             self.show_error(f"'{os.path.basename(fd_path)}' が見つかりません。"); return

        # --- fdコマンドの組み立て ---
        cmd = [fd_path, keyword, folder, "--absolute-path"]
        if self.type_var.get() in ("f", "d"): cmd += ["-t", self.type_var.get()]
        if self.include_hidden_var.get(): cmd.append("--hidden")
        cmd.append("--case-sensitive" if self.case_sensitive_var.get() else "--ignore-case")

        # --- コマンド実行 ---
        try:
            # CREATE_NO_WINDOWで実行時の黒いコンソール表示を抑制
            creation_flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8",
                errors='ignore', creationflags=creation_flags
            )

            # --- 結果処理 ---
            if result.returncode in (0, 1): # fdは結果0件でもリターンコード1を返すことがある
                files = result.stdout.strip().splitlines()
                self.after(0, lambda: self.show_results(files))
            else:
                self.show_error(f"fd 実行エラー:\n{result.stderr}")
        except FileNotFoundError:
             self.show_error(f"'{os.path.basename(fd_path)}' が見つかりません。")
        except Exception as e:
            self.show_error(f"予期せぬエラーが発生しました: {e}")
        finally:
            # 検索終了後、UIを通常状態に戻す
            self.after(0, self.on_keyword_change)
            self.after(0, lambda: self.search_button.config(text="検索開始"))

    def show_results(self, files: list):
        """検索結果をリストボックスに表示する。"""
        if not files or files == ['']:
            self.result_listbox.insert("end", "一致するファイルは見つかりませんでした。")
            self.status_var.set("⚠ 一致するファイルはありませんでした。")
        else:
            for f in files:
                self.result_listbox.insert("end", f)
            self.status_var.set(f"✅ 検索完了（{len(files)}件）")
        # 結果表示後、テーマ色を再適用して表示崩れを防ぐ
        self.change_theme(self.style.theme.name)

    def open_selected_path(self, event=None):
        """選択したアイテムをOSのデフォルトアプリケーションで開く（ダブルクリック時の動作）。"""
        selection = self.result_listbox.curselection()
        if not selection: return

        path = self.result_listbox.get(selection[0])
        if not os.path.exists(path):
            messagebox.showwarning("警告", "選択されたパスは存在しません。"); return

        try:
            # os.startfileはWindows専用。他OSはsubprocessで対応。
            if platform.system() == "Windows":
                os.startfile(os.path.normpath(path))
            else:
                 subprocess.run(['open' if platform.system() == "Darwin" else 'xdg-open', path], check=True)
        except Exception as e:
            messagebox.showerror("エラー", f"ファイル/フォルダを開けませんでした: {e}")

    def show_error(self, msg: str):
        """エラーメッセージをダイアログで表示し、UIをリセットする。"""
        # messageboxはメインスレッドで実行する必要があるためself.afterを使用
        self.after(0, lambda: messagebox.showerror("エラー", msg))
        self.after(0, self.on_keyword_change)
        self.after(0, lambda: self.status_var.set("❌ エラーが発生しました"))

if __name__ == "__main__":
    # アプリケーションのエントリーポイント
    app = FdSearchApp(themename="solar")
    app.mainloop()
