import sys
from cx_Freeze import setup, Executable

# --- アプリケーションの基本情報 ---
# これらの値は、作成されるexeファイルのプロパティなどに使用されます。
APP_NAME = "fd ファイル検索ツール"
APP_VERSION = "1.1.0"
SCRIPT_FILE = "main.py"
APP_DESCRIPTION = "A simple GUI wrapper for the 'fd' command."
ICON_FILE = "icon/icon.ico"


# --- ビルドオプション ---

# 実行プラットフォームに応じてベースを決定
# baseを"Win32GUI"に設定すると、Windowsで実行した際に
# 後ろに表示される黒いコンソールウィンドウを非表示にできます。
base = "Win32GUI" if sys.platform == "win32" else None

# build_exeオプション: ビルド時の詳細な挙動を制御
build_exe_options = {
    # packages: cx_Freezeが自動で見つけにくいパッケージを明示的に指定。
    # ttkbootstrapはテーマデータなどを含むため、指定しておくと安全です。
    "packages": ["os", "tkinter", "ttkbootstrap", "threading", "platform"],

    # includes/excludes: 特定のモジュールを強制的に含めたり、除外したりする場合に指定。
    # 今回は特に不要なため空にしています。
    "includes": [],
    "excludes": [],

    # include_files: Pythonスクリプト以外の、exeに同梱したいファイルやフォルダを指定。
    # (コピー元のパス, ビルド先でのパス) のタプル形式で指定します。
    # 'icon/' のようにフォルダだけ指定すると、フォルダごとコピーされます。
    "include_files": [
        "icon/",      # iconフォルダとその中身
        "fd.exe"      # fd.exe本体
    ]
}

# --- 実行可能ファイル(Executable)の定義 ---
# 実際にビルドされるexeファイルの設定です。
executables = [
    Executable(
        SCRIPT_FILE,          # メインとなるスクリプトファイル
        base=base,            # コンソール非表示設定
        target_name=f"{APP_NAME}.exe", # 出力されるexeのファイル名
        icon=ICON_FILE        # exeファイルに適用するアイコン
    )
]


# --- セットアップの実行 ---
# 上記で定義した設定を元に、ビルドプロセスを実行します。
setup(
    name=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    options={"build_exe": build_exe_options},
    executables=executables
)
