import socket
import time
import requests
import threading
import json
import os
import mss
from PIL import Image
import io
import asyncio
import websockets
import subprocess
import ctypes

# ===== 사용자 입력 유휴 시간 감지 (1분 이상 무반응 측정) =====
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', ctypes.c_uint),
        ('dwTime', ctypes.c_uint)
    ]

def get_idle_seconds():
    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
    except:
        pass
    return 0.0

# ===== 화면/전원 제어 =====
SC_MONITORPOWER = 0xF170
WM_SYSCOMMAND = 0x0112
HWND_BROADCAST = 0xFFFF

def set_monitor_power(on: bool):
    try:
        if on:
            try: log("MONITOR_POWER: 켜기(Wake-up) 시작...")
            except: print("[Monitor] Waking display...")

            # 1. Windows 전원 관리자에게 시스템 및 디스플레이 즉각 활성화 선언
            # ES_CONTINUOUS(0x80000000) | ES_DISPLAY_REQUIRED(0x00000002) | ES_SYSTEM_REQUIRED(0x00000001)
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000002 | 0x00000001)

            # 2. WM_SYSCOMMAND SC_MONITORPOWER -1 브로드캐스트 (일부 WDDM 드라이버 호환)
            try:
                ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, -1)
                ctypes.windll.user32.DefWindowProcW(ctypes.windll.user32.GetDesktopWindow(), WM_SYSCOMMAND, SC_MONITORPOWER, -1)
            except:
                pass

            # 3. 마우스 현재 좌표
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            pt = POINT()
            has_pt = False
            try:
                if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                    has_pt = True
            except:
                pass

            # 4. Windows 10/11 디스플레이를 깨우는 핵심 하드웨어 인터럽트 에뮬레이션 (3회 반복)
            VK_SHIFT = 0x10
            KEYEVENTF_KEYUP = 0x0002
            MOUSEEVENTF_MOVE = 0x0001

            for _ in range(3):
                # (a) Shift 키 입력 (입력창 오염 없이 DWM 절전 해제)
                ctypes.windll.user32.keybd_event(VK_SHIFT, 0, 0, 0)
                time.sleep(0.02)
                ctypes.windll.user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)

                # (b) 마우스 80px 이동 (노이즈 필터링 통과) 후 복귀
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, 80, 80, 0, 0)
                time.sleep(0.02)
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, -80, -80, 0, 0)

                # (c) SetCursorPos 복원
                if has_pt:
                    ctypes.windll.user32.SetCursorPos(pt.x + 20, pt.y + 20)
                    time.sleep(0.02)
                    ctypes.windll.user32.SetCursorPos(pt.x, pt.y)

                time.sleep(0.04)

            try: log("MONITOR_POWER: 켜기(Wake-up) 완료")
            except: pass
        else:
            try: log("MONITOR_POWER: 끄기 실행")
            except: pass
            # 2: 절전(모니터 끄기)
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2)
    except Exception as e:
        try: log(f"[Error] set_monitor_power: {e}")
        except: print(f"[Error] set_monitor_power: {e}")

# ===== 화면 잠금 (주목하세요! 순수 Win32 API 기반 전체화면 오버레이 + 마우스/키보드 차단) =====
import ctypes.wintypes
from ctypes import wintypes

_user32 = ctypes.windll.user32
_gdi32 = ctypes.windll.gdi32
_kernel32 = ctypes.windll.kernel32

_user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.DefWindowProcW.restype = wintypes.LPARAM

_user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.GetWindowLongPtrW.restype = wintypes.LPARAM

_user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LPARAM]
_user32.SetWindowLongPtrW.restype = wintypes.LPARAM

_gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
_gdi32.SelectObject.restype = wintypes.HANDLE

_WNDPROC = ctypes.WINFUNCTYPE(wintypes.LPARAM, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

class _WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('style', wintypes.UINT),
        ('lpfnWndProc', _WNDPROC),
        ('cbClsExtra', ctypes.c_int),
        ('cbWndExtra', ctypes.c_int),
        ('hInstance', wintypes.HINSTANCE),
        ('hIcon', wintypes.HANDLE),
        ('hCursor', wintypes.HANDLE),
        ('hbrBackground', wintypes.HBRUSH),
        ('lpszMenuName', wintypes.LPCWSTR),
        ('lpszClassName', wintypes.LPCWSTR),
        ('hIconSm', wintypes.HANDLE)
    ]

class _RECT(ctypes.Structure):
    _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG), ('right', wintypes.LONG), ('bottom', wintypes.LONG)]

class _PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ('hdc', wintypes.HDC),
        ('fErase', wintypes.BOOL),
        ('rcPaint', _RECT),
        ('fRestore', wintypes.BOOL),
        ('fIncUpdate', wintypes.BOOL),
        ('rgbReserved', ctypes.c_byte * 32)
    ]

def _overlay_wndproc(hwnd, msg, wparam, lparam):
    if msg == 0x000F:  # WM_PAINT
        ps = _PAINTSTRUCT()
        hdc = _user32.BeginPaint(hwnd, ctypes.byref(ps))
        rect = _RECT()
        _user32.GetClientRect(hwnd, ctypes.byref(rect))

        # 검은색 배경 전체 채우기
        hbrush = _gdi32.CreateSolidBrush(0x000000)
        _user32.FillRect(hdc, ctypes.byref(rect), hbrush)
        _gdi32.DeleteObject(hbrush)

        # 개별 모니터별 맞춤 폰트 적용
        hfont = _user32.GetWindowLongPtrW(hwnd, -21)  # GWL_USERDATA
        old_font = None
        if hfont:
            old_font = _gdi32.SelectObject(hdc, hfont)

        # 노란색 굵은 글씨 (#FFEB3B -> BGR: 0x003BEBFF)
        _gdi32.SetBkMode(hdc, 1)  # TRANSPARENT
        _gdi32.SetTextColor(hdc, 0x003BEBFF)

        text = '주목하세요!'
        tsize = wintypes.SIZE()
        _gdi32.GetTextExtentPoint32W(hdc, text, len(text), ctypes.byref(tsize))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        x = max(0, (w - tsize.cx) // 2)
        y = max(0, (h - tsize.cy) // 2)
        _gdi32.ExtTextOutW(hdc, x, y, 0, None, text, len(text), None)

        if old_font:
            _gdi32.SelectObject(hdc, old_font)

        _user32.EndPaint(hwnd, ctypes.byref(ps))
        return 0
    elif msg in (0x0020, 0x0100, 0x0101, 0x0200, 0x0201, 0x0202, 0x0204, 0x0205):
        # 마우스 커서 숨김 및 모든 입력 차단
        return 1
    elif msg == 0x0010:  # WM_CLOSE
        _user32.DestroyWindow(hwnd)
        return 0
    elif msg == 0x0002:  # WM_DESTROY
        _user32.PostQuitMessage(0)
        return 0
    return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)

overlay_hwnds = []
overlay_fonts = []
overlay_active = False
overlay_lock = threading.Lock()
_wndproc_ref = None

def _run_overlay_thread():
    global overlay_hwnds, overlay_fonts, overlay_active, _wndproc_ref
    try:
        try:
            _user32.SetProcessDPIAware()
        except: pass

        _wndproc_ref = _WNDPROC(_overlay_wndproc)
        hInstance = _kernel32.GetModuleHandleW(None)
        className = f'CIM_Lock_Overlay_{int(time.time()*1000)}'

        wc = _WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(_WNDCLASSEXW)
        wc.style = 3  # CS_HREDRAW | CS_VREDRAW
        wc.lpfnWndProc = _wndproc_ref
        wc.hInstance = hInstance
        wc.hbrBackground = _gdi32.CreateSolidBrush(0x000000)
        wc.lpszClassName = className
        _user32.RegisterClassExW(ctypes.byref(wc))

        # 모든 모니터의 해상도 및 위치 측정
        monitors_info = []
        def monitor_enum_proc(hmon, hdc, lprect, lparam):
            r = lprect.contents
            w = r.right - r.left
            h = r.bottom - r.top
            font_h = max(45, int(h * 0.08))  # 모니터 높이에 비례하는 선명한 폰트 크기
            monitors_info.append((r.left, r.top, w, h, font_h))
            return 1

        _MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HANDLE, wintypes.HDC, ctypes.POINTER(_RECT), wintypes.LPARAM)
        _user32.EnumDisplayMonitors(0, 0, _MONITORENUMPROC(monitor_enum_proc), 0)

        if not monitors_info:
            vx = _user32.GetSystemMetrics(76)
            vy = _user32.GetSystemMetrics(77)
            vw = _user32.GetSystemMetrics(78)
            vh = _user32.GetSystemMetrics(79)
            monitors_info = [(vx, vy, vw, vh, max(45, int(vh * 0.08)))]

        with overlay_lock:
            overlay_hwnds = []
            overlay_fonts = []
            for (x, y, w, h, font_h) in monitors_info:
                hfont = _gdi32.CreateFontW(-font_h, 0, 0, 0, 700, 0, 0, 0, 1, 0, 0, 0, 0, '맑은 고딕')
                overlay_fonts.append(hfont)
                hwnd = _user32.CreateWindowExW(
                    0x00000008,  # WS_EX_TOPMOST
                    className,
                    'CIM_ATTENTION_OVERLAY',
                    0x90000000,  # WS_VISIBLE | WS_POPUP
                    x, y, w, h,
                    0, 0, hInstance, 0
                )
                if hwnd:
                    _user32.SetWindowLongPtrW(hwnd, -21, hfont)
                    overlay_hwnds.append(hwnd)
                    _user32.SetWindowPos(hwnd, -1, x, y, w, h, 0x0040 | 0x0001 | 0x0002)  # HWND_TOPMOST, SWP_SHOWWINDOW
                    _user32.UpdateWindow(hwnd)

        msg = wintypes.MSG()
        while overlay_active:
            while _user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1):
                _user32.TranslateMessage(ctypes.byref(msg))
                _user32.DispatchMessageW(ctypes.byref(msg))

            with overlay_lock:
                for h in overlay_hwnds:
                    _user32.BringWindowToTop(h)
            time.sleep(0.05)

        with overlay_lock:
            for h in overlay_hwnds:
                _user32.DestroyWindow(h)
            for f in overlay_fonts:
                _gdi32.DeleteObject(f)
            overlay_hwnds = []
            overlay_fonts = []
    except Exception as e:
        print(f'[Error] overlay thread: {e}')
    finally:
        with overlay_lock:
            overlay_hwnds = []
            overlay_fonts = []

def show_attention_overlay():
    global overlay_active
    with overlay_lock:
        if overlay_active:
            return
        overlay_active = True

    try: log("SCREEN_LOCKED: '주목하세요!' 오버레이 및 키보드/마우스 입력 차단 시작")
    except: print("[Lock] Attention overlay ON")

    # 1. 학생 물리적 키보드 및 마우스 입력 차단 (BlockInput)
    try:
        ctypes.windll.user32.BlockInput(True)
    except Exception as e:
        print(f"[BlockInput Error] {e}")

    # 2. 순수 Win32 전체화면 오버레이 스레드 실행
    t = threading.Thread(target=_run_overlay_thread, daemon=True)
    t.start()

def hide_attention_overlay():
    global overlay_active
    with overlay_lock:
        if not overlay_active:
            return
        overlay_active = False

    try: log("SCREEN_UNLOCKED: '주목하세요!' 해제 및 키보드/마우스 복구")
    except: print("[Lock] Attention overlay OFF")

    # 학생 물리적 키보드 및 마우스 입력 차단 해제 (BlockInput)
    try:
        ctypes.windll.user32.BlockInput(False)
    except Exception as e:
        print(f"[UnblockInput Error] {e}")

    # 3. 화면 활성화 신호 전송
    try:
        VK_SHIFT = 0x10
        KEYEVENTF_KEYUP = 0x0002
        ctypes.windll.user32.keybd_event(VK_SHIFT, 0, 0, 0)
        time.sleep(0.02)
        ctypes.windll.user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
    except Exception:
        pass

def lock_workstation():
    show_attention_overlay()

def power_action(action):
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        cf = 0x08000000  # CREATE_NO_WINDOW
        if action == "shutdown":
            subprocess.run(["shutdown", "/s", "/f", "/t", "0"], startupinfo=si, creationflags=cf)
        elif action == "restart":
            subprocess.run(["shutdown", "/r", "/f", "/t", "0"], startupinfo=si, creationflags=cf)
        elif action == "logoff":
            subprocess.run(["shutdown", "/l"], startupinfo=si, creationflags=cf)
        elif action == "cancel_shutdown":
            subprocess.run(["shutdown", "/a"], startupinfo=si, creationflags=cf)
    except Exception as e:
        print(f"[Error] power_action: {e}")

# ===== 원격 마우스/키보드 제어 (SendInput, 표준 win32 구조체) =====
PUL = ctypes.POINTER(ctypes.c_ulong)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short), ("wParamH", ctypes.c_ushort)]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("union", INPUT_UNION)]

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
KEYEVENTF_KEYUP = 0x0002

def _send_input(inp):
    ctypes.windll.user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))

def move_mouse_abs(x, y):
    vx = ctypes.windll.user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
    vy = ctypes.windll.user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
    vw = ctypes.windll.user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    vh = ctypes.windll.user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
    nx = int((x - vx) * 65535 / max(vw - 1, 1))
    ny = int((y - vy) * 65535 / max(vh - 1, 1))
    mi = MOUSEINPUT(nx, ny, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, 0, None)
    _send_input(INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi)))

def click_mouse(button="left", down=True):
    if button == "right":
        flags = MOUSEEVENTF_RIGHTDOWN if down else MOUSEEVENTF_RIGHTUP
    else:
        flags = MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP
    mi = MOUSEINPUT(0, 0, 0, flags, 0, None)
    _send_input(INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi)))

def send_key(vk_code, down=True):
    flags = 0 if down else KEYEVENTF_KEYUP
    ki = KEYBDINPUT(vk_code, 0, flags, 0, None)
    _send_input(INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=ki)))

def get_monitor_rect(monitor_index):
    try:
        with mss.mss() as sct:
            mons = sct.monitors
            if 1 <= monitor_index < len(mons):
                return mons[monitor_index]
    except Exception:
        pass
    return None

def remote_mouse_move(monitor_index, rx, ry):
    rect = get_monitor_rect(monitor_index)
    if not rect:
        return
    x = rect["left"] + rx * rect["width"]
    y = rect["top"] + ry * rect["height"]
    move_mouse_abs(int(x), int(y))

# ===== 프로세스 수집/차단 =====
SAFE_PROCESSES = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe",
    "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe", "svchost.exe",
    "explorer.exe", "dwm.exe", "fontdrvhost.exe", "sihost.exe", "taskhostw.exe",
    "ctfmon.exe", "conhost.exe", "cim_agent_pro.exe", "python.exe", "pythonw.exe",
}

def get_process_list():
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        cf = 0x08000000  # CREATE_NO_WINDOW
        out = subprocess.check_output(
            ["tasklist", "/fo", "csv", "/nh"],
            stderr=subprocess.DEVNULL, timeout=5,
            startupinfo=si,
            creationflags=cf
        ).decode("cp949", errors="ignore")
        names = []
        for line in out.strip().splitlines():
            parts = [p.strip('"') for p in line.split('","')]
            if parts and parts[0].lstrip('"'):
                names.append(parts[0].lstrip('"'))
        return sorted(set(names))
    except Exception:
        return []

def kill_process(name):
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        cf = 0x08000000  # CREATE_NO_WINDOW
        subprocess.run(
            ["taskkill", "/F", "/IM", name],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
            startupinfo=si,
            creationflags=cf
        )
    except Exception:
        pass

# 교사용 서버 설정
SERVER_IP = "10.128.56.41"
SERVER_URL = f"http://{SERVER_IP}:8888"
WS_URL = f"ws://{SERVER_IP}:8888/ws"

def resolve_server_ip():
    global SERVER_IP, SERVER_URL, WS_URL
    # 1. Check for server_ip.txt
    if os.path.exists("server_ip.txt"):
        try:
            with open("server_ip.txt", "r", encoding="utf-8") as f:
                ip = f.read().strip()
                if ip:
                    SERVER_IP = ip
                    SERVER_URL = f"http://{SERVER_IP}:8888"
                    WS_URL = f"ws://{SERVER_IP}:8888/ws"
                    print(f"[IP] Loaded from server_ip.txt: {SERVER_IP}")
                    return
        except:
            pass

    # 2. Try connection to default hardcoded IP
    print(f"[IP] Using default server IP: {SERVER_IP}")

hostname = socket.gethostname()
CLIENT_ID = hostname # 201-XX 형식을 그대로 사용합니다.

def log(msg):
    ts = time.strftime("%H:%M:%S")
    full_msg = f"[{ts}] {msg}"
    try:
        print(full_msg)
        requests.post(f"{SERVER_URL}/log/{CLIENT_ID}", json={"message": msg}, timeout=2)
    except: pass

def run_full_diagnostics():
    log("5단계 자동 확인 시퀀스 시작...")
    
    # 1. PING Test
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        res = subprocess.run(
            ["ping", "-n", "1", SERVER_IP],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            startupinfo=si, creationflags=0x08000000
        ).returncode
        if res == 0: log("STEP1: PING SUCCESS")
        else: raise Exception("Ping Failed")
    except: log("STEP1: PING FAILED"); return

    # 2. Python & Library Check
    try:
        import mss, PIL, websockets
        log("STEP2: PYTHON & LIB OK")
    except: log("STEP2: LIB MISSING"); return

    # 3. Server Port 8888 Check
    try:
        s = socket.socket()
        s.settimeout(2)
        s.connect((SERVER_IP, 8888))
        s.close()
        log("STEP3: PORT 8888 OPEN")
    except: log("STEP3: PORT CLOSED"); return

    # 4. Upload/Server Check
    try:
        requests.get(SERVER_URL, timeout=2)
        log("STEP4: SERVER ACCESSIBLE")
    except: log("STEP4: SERVER TIMEOUT"); return

    # 5. Final Success
    log("STEP5_SUCCESS")

def capture_and_send():
    import hashlib
    import urllib.parse
    last_update_check = 0
    update_interval = 60  # 60초마다 서버의 파일 변경 사항 확인 (트래픽 최소화)
    
    with mss.mss() as sct:
        while True:
            current_time = time.time()
            if current_time - last_update_check > update_interval:
                last_update_check = current_time
                try:
                    # 1. 로컬에 저장된 에이전트 소스 파일의 MD5 해시값 계산
                    local_hash = ""
                    if os.path.exists("FINAL_AGENT_PRO.py"):
                        with open("FINAL_AGENT_PRO.py", "rb") as f:
                            local_hash = hashlib.md5(f.read()).hexdigest()
                    
                    # 2. 서버에 이 해시값 전달하여 최신 파일이 있는지 확인
                    res = requests.get(f"{SERVER_URL}/check_update?hash={local_hash}", timeout=3)
                    if res.status_code == 200 and res.json().get("update_needed"):
                        log("[UPDATE] New agent code version detected. Downloading latest code...")
                        dl = requests.get(f"{SERVER_URL}/download_agent", timeout=5)
                        if dl.status_code == 200 and b"def run():" in dl.content:
                            with open("FINAL_AGENT_PRO.py", "wb") as f:
                                f.write(dl.content)
                            log("[UPDATE] Code updated successfully. Reloading process...")
                            import subprocess
                            si = subprocess.STARTUPINFO()
                            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                            si.wShowWindow = 0
                            subprocess.Popen([sys.executable] + sys.argv[1:], startupinfo=si, creationflags=0x08000000)
                            os._exit(0)
                except Exception as e:
                    print(f"\n[Loader] Update check failed: {e}")

            # 현재 활성화된 창 이름 가져오기 (Windows API)
            active_title = ""
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                if hwnd != 0:
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                        active_title = buf.value
            except:
                pass

            # 사용자 키보드/마우스 입력 유휴 시간(초) 측정
            idle_sec = int(get_idle_seconds())

            try:
                # 모니터 개수 확인 (sct.monitors[0]은 전체 영역)
                monitors = sct.monitors
                for i in range(1, len(monitors)):
                    s = sct.grab(monitors[i])
                    img = Image.frombytes("RGB", s.size, s.bgra, "raw", "BGRX")
                    # 원본 해상도 그대로 전송하여 확대 시에도 최고의 선명도 유지 (예: 1920x1080)
                    buf = io.BytesIO()
                    img.save(buf, format='JPEG', quality=70)
                    
                    # 파일명에 모니터 번호 추가 (예: 201-01-1)
                    target_id = f"{CLIENT_ID}-{i}"
                    safe_title = urllib.parse.quote(active_title)
                    requests.post(f"{SERVER_URL}/upload_screen/{target_id}?title={safe_title}&idle_sec={idle_sec}", 
                                   files={"file": ("s.jpg", buf.getvalue(), "image/jpeg")}, timeout=3)
                
                print(f"\r[{time.strftime('%H:%M:%S')}] Screen sent (Monitors: {len(monitors)-1})", end="", flush=True)
            except Exception as e:
                print(f"\n[Error] Capture: {e}")
            time.sleep(1.0)

async def websocket_handler():
    while True:
        try:
            async with websockets.connect(f"{WS_URL}/{CLIENT_ID}") as ws:
                log("Connected to Server WebSocket")
                while True:
                    message = await ws.recv()
                    data = json.loads(message)
                    command = data.get("command")
                    
                    if command == "verify_step5":
                        # 동기 함수인 진단로직을 별도 스레드에서 실행하거나 
                        # 그냥 호출 (asyncio 루프를 방해하지 않도록 주의)
                        threading.Thread(target=run_full_diagnostics, daemon=True).start()
                    elif command == "internet_off":
                        log("INTERNET_BLOCKED (Simulated)")
                        # 실제 차단 로직은 OS 명령어로 구현 가능
                    elif command == "internet_on":
                        log("INTERNET_ALLOWED (Simulated)")
                    elif command in ("monitor_off", "lock"):
                        log("CMD: SCREEN_LOCK requested (Attention overlay ON)")
                        show_attention_overlay()
                    elif command in ("monitor_on", "unlock"):
                        log("CMD: SCREEN_UNLOCK requested (Attention overlay OFF)")
                        hide_attention_overlay()
                    elif command in ("shutdown", "restart", "logoff", "cancel_shutdown"):
                        log(f"POWER_ACTION: {command}")
                        power_action(command)
                    elif command == "mouse_move":
                        remote_mouse_move(int(data.get("monitor", 1)), float(data.get("rx", 0)), float(data.get("ry", 0)))
                    elif command == "mouse_click":
                        button = data.get("button", "left")
                        click_mouse(button, True)
                        click_mouse(button, False)
                    elif command == "key_press":
                        vk = data.get("vk")
                        if vk:
                            send_key(int(vk), True)
                            send_key(int(vk), False)
        except Exception as e:
            print(f"\n[WS Error] {e}. Retrying in 5s...")
            await asyncio.sleep(5)

def start_ws_loop():
    asyncio.run(websocket_handler())

def process_watch_loop():
    last_report = 0
    last_blocklist_fetch = 0
    blocklist = []
    report_interval = 5
    blocklist_interval = 10
    while True:
        try:
            now = time.time()
            processes = get_process_list()

            if now - last_report > report_interval:
                last_report = now
                try:
                    requests.post(f"{SERVER_URL}/report_processes/{CLIENT_ID}",
                                  json={"processes": processes}, timeout=3)
                except Exception:
                    pass

            if now - last_blocklist_fetch > blocklist_interval:
                last_blocklist_fetch = now
                try:
                    res = requests.get(f"{SERVER_URL}/get_blocklist", timeout=3)
                    if res.status_code == 200:
                        blocklist = res.json()
                except Exception:
                    pass

            if blocklist:
                blocked_lower = {b.lower() for b in blocklist}
                for name in processes:
                    if name.lower() in blocked_lower and name.lower() not in SAFE_PROCESSES:
                        kill_process(name)
                        log(f"[BLOCK] Terminated: {name}")
        except Exception as e:
            print(f"\n[Error] Process watch: {e}")
        time.sleep(2)

def cleanup_previous_agents():
    try:
        my_pid = os.getpid()
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        cf = 0x08000000
        ps_cmd = f"Get-Process -Name '02_학생용*', 'CIM_AGENT*' -ErrorAction SilentlyContinue | Where-Object {{ $_.Id -ne {my_pid} }} | Stop-Process -Force"
        subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                       startupinfo=si, creationflags=cf, timeout=5)
    except Exception:
        pass

def run():
    # 기존 구버전 프로세스 자동 정리
    cleanup_previous_agents()

    # 서버 IP 동적 감지
    resolve_server_ip()

    # 서버 연결 대기
    print(f"Connecting to {SERVER_URL}...")
    for _ in range(10):
        try:
            requests.get(SERVER_URL, timeout=3)
            break
        except: time.sleep(3)

    log(f"Agent started (Dual-Monitor Ready)")
    
    # 웹소켓 리스너 시작
    threading.Thread(target=start_ws_loop, daemon=True).start()

    # 프로세스 수집/차단 감시 시작
    threading.Thread(target=process_watch_loop, daemon=True).start()

    # 화면 전송 시작
    capture_and_send()

if __name__ == "__main__":
    run()
