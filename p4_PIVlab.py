
import os
import subprocess
from typing import Optional, Tuple
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QWidget


def select_pivlab_exe(parent: Optional[QWidget] = None, initial: Optional[str] = None) -> str:
    """
    PIVlab 실행파일(.exe) 선택 대화상자
    """
    if initial and os.path.isdir(initial):
        start_dir = initial
    elif initial and os.path.isfile(initial):
        start_dir = os.path.dirname(initial)
    else:
        start_dir = ""

    exe_path, _ = QFileDialog.getOpenFileName(
        parent, "Select PIVlab Executable",
        directory=start_dir,
        filter="Executable (*.exe);;All Files (*)"
    )
    return exe_path


def select_input_dir(parent: Optional[QWidget] = None) -> Optional[str]:
    """
    입력 폴더(선택 사항) 선택 대화상자
    - PIVlab이 CLI 인자를 지원하면 전달, 아니면 무시됨
    """
    d = QFileDialog.getExistingDirectory(parent, "Select Input Folder (Optional)")
    return d if d else None


def launch_pivlab(exe_path: str, input_dir: Optional[str] = None) -> None:
    """
    PIVlab 실행 (비동기). CLI 인자 미지원이면 input_dir은 무시될 수 있음.
    """
    if not exe_path or not os.path.exists(exe_path):
        raise FileNotFoundError(f"PIVlab 실행파일이 존재하지 않습니다:\n{exe_path}")

    cmd = [exe_path]
    if input_dir:
        cmd.append(input_dir)

    try:
        subprocess.Popen(cmd, shell=False)
    except Exception as e:
        raise RuntimeError(f"PIVlab 실행 중 오류:\n{e}")


def run_pivlab_flow(parent: Optional[QWidget] = None,
                    exe_path: Optional[str] = None,
                    ask_input_dir: bool = True) -> Tuple[str, Optional[str]]:
    """
    전체 흐름:
      - exe 경로 없으면 선택
      - (옵션) 입력 폴더 선택
      - 실행 후 메시지
    Returns: (exe_path, input_dir)
    """
    # 1) EXE 경로
    if not exe_path:
        exe_path = select_pivlab_exe(parent)
        if not exe_path:
            raise RuntimeError("PIVlab 실행파일이 선택되지 않았습니다.")

    # 2) 입력 폴더 (선택)
    input_dir = select_input_dir(parent) if ask_input_dir else None

    # 3) 실행
    launch_pivlab(exe_path, input_dir=input_dir)

    # # 4) 안내
    msg = f"PIVlab 실행을 시작했습니다.\n\n- EXE: {exe_path}"
    if input_dir:
        msg += f"\n- INPUT: {input_dir}"
    QMessageBox.information(parent, "PIVlab", msg)

    return exe_path, input_dir