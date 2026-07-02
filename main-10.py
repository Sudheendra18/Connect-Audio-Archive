import flet as ft
import flet_audio as fa
import json
import os
import math
import datetime
import asyncio
import concurrent.futures

# ─── Pipeline import ─────────────────────────────────────────────────────────
try:
    from audio_pipeline import analyze_audio as _analyze_audio
    _PIPELINE_READY = True
except Exception as _e:
    _PIPELINE_READY = False
    _PIPELINE_ERR   = str(_e)

try:
    from audio_pipeline import check_profanity as _check_profanity
    _PROFANITY_READY = True
except Exception:
    _PROFANITY_READY = False

APP_VERSION   = "1.0.0"
APP_DIR       = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE  = os.path.join(APP_DIR, "analysis_history.json")
SETTINGS_FILE = os.path.join(APP_DIR, "app_settings.json")

LANGUAGES = [
    "English", "French", "German", "Hindi",
    "Kannada", "Korean", "Malayalam", "Spanish",
    "Tamil", "Telugu",
]

# ═══════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM  —  One UI inspired, flat, Samsung-blue primary, dual theme
# ═══════════════════════════════════════════════════════════════════════════════
class Palette:
    def __init__(self, **kw):
        self.__dict__.update(kw)

LIGHT_PAL = Palette(
    BG="#F2F4F8", SURFACE="#FFFFFF", SURFACE_2="#EDF0F6", SURFACE_3="#F6F8FC",
    BORDER="#E6E9F0", BORDER_STRONG="#D6DBE6",
    BRAND="#1B6EF3", BRAND_STRONG="#1457D6", BRAND_SOFT="#E4EDFE",
    ON_BRAND="#FFFFFF", ON_BRAND_MUTED="#C7DAFB",
    TEXT="#0C1322", TEXT_2="#39435A", MUTED="#6A7588", FAINT="#9AA3B4",
    SPEECH="#0EA5A5", SPEECH_SOFT="#D6F1F1",
    MUSIC="#7C5CFC",  MUSIC_SOFT="#E9E3FE",
    NOISE="#E08A00",  NOISE_SOFT="#FBEBCB",
    OK="#12A150", OK_SOFT="#D6F0E0", WARN="#E08A00", WARN_SOFT="#FBEBCB",
    ERR="#E5484D", ERR_SOFT="#FBDDDE",
    NAV_BG="#FFFFFF", NAV_INDICATOR="#E4EDFE",
    NAV_SEL_ICON="#1B6EF3", NAV_ICON="#8A93A4",
    NAV_LABEL="#8A93A4", NAV_LABEL_SEL="#1B6EF3",
    RING_TRACK="#E9EDF5", WHITE="#FFFFFF",
)

DARK_PAL = Palette(
    BG="#0B0C11", SURFACE="#16181F", SURFACE_2="#212530", SURFACE_3="#1B1E27",
    BORDER="#272B36", BORDER_STRONG="#343A48",
    BRAND="#3B82F6", BRAND_STRONG="#2E6FE0", BRAND_SOFT="#16233B",
    ON_BRAND="#FFFFFF", ON_BRAND_MUTED="#CBDDFB",
    TEXT="#F4F6FA", TEXT_2="#C3CBD8", MUTED="#8A93A2", FAINT="#5B6473",
    SPEECH="#2DC6C6", SPEECH_SOFT="#0F2E2E",
    MUSIC="#9E86FF",  MUSIC_SOFT="#211C3A",
    NOISE="#F4A63A",  NOISE_SOFT="#33260F",
    OK="#2DB96E", OK_SOFT="#10301E", WARN="#F4A63A", WARN_SOFT="#33260F",
    ERR="#F26269", ERR_SOFT="#341A1C",
    NAV_BG="#121319", NAV_INDICATOR="#1B2A45",
    NAV_SEL_ICON="#5B95F7", NAV_ICON="#7B8494",
    NAV_LABEL="#7B8494", NAV_LABEL_SEL="#6AA0F8",
    RING_TRACK="#272B36", WHITE="#FFFFFF",
)

HERO_TRACK = "#33FFFFFF"
HERO_SOFT  = "#1FFFFFFF"
HERO_HOVER = "#EAF0FD"

IS_DARK = False
P = LIGHT_PAL

DISPLAY_FONT = "Manrope"
BODY_FONT    = "Manrope"
MANROPE_URL  = "https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/Manrope%5Bwght%5D.ttf"
def set_palette(dark):
    global P, IS_DARK
    IS_DARK = dark
    P = DARK_PAL if dark else LIGHT_PAL
def apply_page_theme(page):
    page.theme_mode = ft.ThemeMode.DARK if IS_DARK else ft.ThemeMode.LIGHT
    page.bgcolor = P.BG
def _load_settings():
    global IS_DARK
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                IS_DARK = bool(json.load(f).get("dark", False))
        except Exception:
            pass
def _save_settings():
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump({"dark": IS_DARK}, f)
    except Exception:
        pass
# ─── History Manager ─────────────────────────────────────────────────────────
class HistoryManager:
    def __init__(self):
        self.records = []
        self._load()

    def _load(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE) as f:
                    self.records = json.load(f)
            except Exception:
                self.records = []

    def _save(self):
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.records, f, indent=2)

    def add(self, record: dict):
        self.records.insert(0, record)
        if len(self.records) > 100:
            self.records = self.records[:100]
        self._save()

    def clear(self):
        self.records = []
        self._save()

    def export(self) -> str:
        lines = ["Audio Classifier - Analysis History", "=" * 40]
        for r in self.records:
            lines.append(f"\nDate      : {r.get('timestamp','N/A')}")
            lines.append(f"File      : {r.get('filename','N/A')}")
            lines.append(f"Type      : {r.get('audio_type','N/A')}")
            if r.get("language"):
                lines.append(f"Language  : {r['language']}")
            lines.append(f"Duration  : {r.get('duration','N/A')}")
            lines.append("-" * 30)
        return "\n".join(lines)

    def stats(self):
        total  = len(self.records)
        speech = sum(1 for r in self.records if r.get("audio_type") == "Speech")
        music  = sum(1 for r in self.records if r.get("audio_type") == "Music")
        noise  = sum(1 for r in self.records if r.get("audio_type") == "Noise")
        lang_dist = {}
        for r in self.records:
            if r.get("language"):
                lang_dist[r["language"]] = lang_dist.get(r["language"], 0) + 1
        return {"total": total, "speech": speech,
                "music": music, "noise": noise, "lang_dist": lang_dist}
# ─── App State ───────────────────────────────────────────────────────────────
class AppState:
    def __init__(self):
        self.history_mgr    = HistoryManager()
        self.last_result    = None
        self.current_file   = None
        self.file_picker    = None
        self.playing_path   = None   # filepath currently loaded in the player
        self.is_playing     = False
        self.current_screen = "home"

state = AppState()
# ─── Pipeline helpers ────────────────────────────────────────────────────────
def _format_duration(seconds: float) -> str:
    if seconds is None:
        return "N/A"
    seconds = max(0.0, float(seconds))
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"

def _get_audio_duration(audio_path: str) -> str:
    if not audio_path or not os.path.exists(audio_path):
        return "N/A"
    try:
        import librosa
        try:
            seconds = librosa.get_duration(path=audio_path)
        except TypeError:
            seconds = librosa.get_duration(filename=audio_path)
        return _format_duration(seconds)
    except Exception:
        pass
    try:
        import wave
        with wave.open(audio_path, "rb") as w:
            frames = w.getnframes()
            rate   = w.getframerate()
            if rate:
                return _format_duration(frames / float(rate))
    except Exception:
        pass
    try:
        import soundfile as sf
        info = sf.info(audio_path)
        return _format_duration(info.duration)
    except Exception:
        pass
    return "N/A"

def _run_pipeline_sync(audio_path: str) -> dict:
    if not _PIPELINE_READY:
        raise RuntimeError(
            f"Could not import audio_pipeline.\nError: {_PIPELINE_ERR}\n\n"
            "Make sure audio_pipeline.py, svm_model.pkl and scaler.pkl "
            "are in the same folder as main.py."
        )
    return _analyze_audio(audio_path)

def _analyze_with_duration(audio_path: str):
    result = _run_pipeline_sync(audio_path)
    duration = _get_audio_duration(audio_path)
    return result, duration
# ─── Type helpers ────────────────────────────────────────────────────────────
def _type_color(t):
    return {"Speech": P.SPEECH, "Music": P.MUSIC, "Noise": P.NOISE}.get(t, P.BRAND)

def _type_soft(t):
    return {"Speech": P.SPEECH_SOFT, "Music": P.MUSIC_SOFT, "Noise": P.NOISE_SOFT}.get(t, P.BRAND_SOFT)

def _type_icon(t):
    return {
        "Speech": ft.Icons.MIC_ROUNDED,
        "Music":  ft.Icons.MUSIC_NOTE_ROUNDED,
        "Noise":  ft.Icons.GRAPHIC_EQ_ROUNDED,
    }.get(t, ft.Icons.HELP_OUTLINE_ROUNDED)
# ═══════════════════════════════════════════════════════════════════════════════
# PRIMITIVES
# ═══════════════════════════════════════════════════════════════════════════════
def T(text, size=14, color=None, weight=ft.FontWeight.NORMAL, align=None, font=None):
    return ft.Text(
        text, size=size,
        color=color or P.TEXT_2,
        weight=weight,
        font_family=font or BODY_FONT,
        text_align=align or ft.TextAlign.LEFT,
    )

def D(text, size=24, color=None, weight=ft.FontWeight.W_800, align=None):
    return T(text, size=size, color=color or P.TEXT, weight=weight, align=align, font=DISPLAY_FONT)

def divider():
    return ft.Container(height=1, bgcolor=P.BORDER)

def card(content, pad=18, radius=22, bg=None, border=True, border_color=None):
    return ft.Container(
        content=content,
        bgcolor=bg or P.SURFACE,
        border_radius=radius,
        padding=pad,
        border=ft.Border.all(1, border_color or P.BORDER) if border else None,
    )

def section_title(txt):
    return ft.Container(
        T(txt.upper(), size=11, color=P.MUTED, weight=ft.FontWeight.W_700),
        padding=ft.Padding(left=4, right=0, top=4, bottom=2),
    )

def icon_square(icon, fg, bg, size=38, isz=18, radius=13):
    return ft.Container(
        ft.Icon(icon, color=fg, size=isz),
        width=size, height=size,
        bgcolor=bg, border_radius=radius,
        alignment=ft.alignment.Alignment(0, 0),
    )

def chip(label, fg, bg, size=11):
    return ft.Container(
        T(label, size=size, color=fg, weight=ft.FontWeight.W_700),
        bgcolor=bg, border_radius=100,
        padding=ft.Padding(left=11, right=11, top=6, bottom=6),
    )

def status_pill(text, dot_color):
    return ft.Container(
        ft.Row([
            ft.Container(width=8, height=8, border_radius=4, bgcolor=dot_color),
            T(text, size=12, color=P.MUTED, weight=ft.FontWeight.W_500),
        ], spacing=8, tight=True),
        bgcolor=P.SURFACE_2, border_radius=100,
        padding=ft.Padding(left=12, right=14, top=7, bottom=7),
    )

def pill_button(label, icon, on_click, kind="brand", expand=False, ref=None):
    if kind == "onbrand":
        fg, bg, hov, side = P.BRAND, P.WHITE, HERO_HOVER, ft.BorderSide(0, "transparent")
    elif kind == "ghost":
        fg, bg, hov, side = P.TEXT, "transparent", P.SURFACE_2, ft.BorderSide(1.5, P.BORDER_STRONG)
    else:
        fg, bg, hov, side = P.ON_BRAND, P.BRAND, P.BRAND_STRONG, ft.BorderSide(0, "transparent")
    return ft.Button(
        ref=ref,
        content=ft.Row([
            ft.Icon(icon, size=17, color=fg),
            T(label, size=14, color=fg, weight=ft.FontWeight.W_700),
        ], spacing=9, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        on_click=on_click, expand=expand,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT:  bg,
                ft.ControlState.HOVERED:  hov,
                ft.ControlState.DISABLED: P.SURFACE_2,
            },
            side={ft.ControlState.DEFAULT: side},
            shape=ft.RoundedRectangleBorder(radius=100),
            padding=ft.Padding(left=26, right=26, top=16, bottom=16),
        ),
    )

def back_btn(on_click):
    return ft.IconButton(
        ft.Icons.ARROW_BACK_ROUNDED, on_click=on_click,
        icon_color=P.TEXT, icon_size=20,
        style=ft.ButtonStyle(
            bgcolor={ft.ControlState.DEFAULT: P.SURFACE_2, ft.ControlState.HOVERED: P.SURFACE_3},
            shape=ft.RoundedRectangleBorder(radius=100),
            padding=ft.Padding(left=9, right=9, top=9, bottom=9),
        ),
    )

def chevron_btn(on_click, color):
    return ft.IconButton(
        ft.Icons.CHEVRON_RIGHT_ROUNDED, on_click=on_click,
        icon_color=color, icon_size=20,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
    )

def list_row(icon, fg, soft, title, subtitle=None, trailing=None, value=None):
    mid = [T(title, size=15, color=P.TEXT, weight=ft.FontWeight.W_700)]
    if subtitle:
        mid.append(T(subtitle, size=12, color=P.MUTED))
    row = [icon_square(icon, fg, soft), ft.Column(mid, spacing=2, expand=True)]
    if trailing is not None:
        row.append(trailing)
    elif value is not None:
        row.append(T(value, size=14, color=P.TEXT, weight=ft.FontWeight.W_700))
    return ft.Container(
        ft.Row(row, spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(left=14, right=12, top=14, bottom=14),
    )

def group(rows, bg=None):
    ch = []
    for i, r in enumerate(rows):
        if i > 0:
            ch.append(ft.Container(
                ft.Container(height=1, bgcolor=P.BORDER),
                padding=ft.Padding(left=16, right=16, top=0, bottom=0),
            ))
        ch.append(r)
    return ft.Container(
        ft.Column(ch, spacing=0),
        bgcolor=bg or P.SURFACE, border_radius=22,
        border=ft.Border.all(1, P.BORDER),
    )

def empty_state(icon, title, subtitle):
    inner = ft.Column([
        ft.Container(
            ft.Icon(icon, size=30, color=P.FAINT),
            width=66, height=66, border_radius=66,
            bgcolor=P.SURFACE_2, alignment=ft.alignment.Alignment(0, 0),
        ),
        ft.Container(height=14),
        D(title, size=17, color=P.TEXT, align=ft.TextAlign.CENTER),
        ft.Container(height=4),
        T(subtitle, size=13, color=P.MUTED, align=ft.TextAlign.CENTER),
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)
    return ft.Container(
        content=inner, bgcolor=P.SURFACE, border_radius=22,
        border=ft.Border.all(1, P.BORDER), padding=36,
        alignment=ft.alignment.Alignment(0, 0),
    )

def stat_tile(value, label, fg, soft, icon, brand=False):
    if brand:
        bg, num_c, lbl_c = P.BRAND, P.ON_BRAND, P.ON_BRAND_MUTED
        isq = icon_square(icon, P.WHITE, HERO_SOFT, size=34, isz=16, radius=11)
        border = None
    else:
        bg, num_c, lbl_c = P.SURFACE, fg, P.MUTED
        isq = icon_square(icon, fg, soft, size=34, isz=16, radius=11)
        border = ft.Border.all(1, P.BORDER)
    return ft.Container(
        ft.Column([
            ft.Row([isq, ft.Container(expand=True)]),
            ft.Container(height=12),
            D(str(value), size=28, color=num_c),
            T(label, size=12, color=lbl_c, weight=ft.FontWeight.W_500),
        ], spacing=2),
        bgcolor=bg, border_radius=20, padding=16, border=border, expand=True,
    )

def spec_card(title, items, fg, soft, icon):
    rows = [
        ft.Row([
            T(k, size=12, color=P.MUTED),
            ft.Container(expand=True),
            T(v, size=12, color=P.TEXT, weight=ft.FontWeight.W_600),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
        for k, v in items.items()
    ]
    return card(ft.Column([
        ft.Row([
            icon_square(icon, fg, soft),
            D(title, size=16, color=P.TEXT),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        divider(),
        *rows,
    ], spacing=12))
# ─── Signature element: concentric ring ──────────────────────────────────────
def ring(icon, ring_color, inner_bg, icon_color, size=116, stroke=9, icon_size=40):
    inner = size - 2 * stroke
    return ft.Container(
        content=ft.Container(
            content=ft.Icon(icon, color=icon_color, size=icon_size),
            width=inner, height=inner, border_radius=inner, bgcolor=inner_bg,
            alignment=ft.alignment.Alignment(0, 0),
        ),
        width=size, height=size, border_radius=size, bgcolor=ring_color,
        alignment=ft.alignment.Alignment(0, 0),
    )

def _center_layer(child, box):
    return ft.Container(content=child, width=box, height=box,
                        alignment=ft.alignment.Alignment(0, 0))
# ─── Theme switching ──────────────────────────────────────────────────────────
def _mk_theme_handler(page, navigate, target):
    async def _h(e):
        await set_theme(page, navigate, target)
    return _h

async def set_theme(page, navigate, dark):
    set_palette(dark)
    _save_settings()
    apply_page_theme(page)
    await navigate(state.current_screen)

def theme_icon_button(page, navigate):
    icon = ft.Icons.DARK_MODE_ROUNDED if IS_DARK else ft.Icons.LIGHT_MODE_ROUNDED
    return ft.IconButton(
        icon, icon_color=P.TEXT_2, icon_size=20,
        on_click=_mk_theme_handler(page, navigate, not IS_DARK),
        style=ft.ButtonStyle(
            bgcolor={ft.ControlState.DEFAULT: P.SURFACE_2, ft.ControlState.HOVERED: P.SURFACE_3},
            shape=ft.RoundedRectangleBorder(radius=100),
            padding=ft.Padding(left=10, right=10, top=10, bottom=10),
        ),
    )

def theme_segment(page, navigate):
    def seg(label, icon, target):
        active = (IS_DARK == target)
        fg = P.ON_BRAND if active else P.TEXT_2
        return ft.Button(
            content=ft.Row([
                ft.Icon(icon, size=16, color=fg),
                T(label, size=13, color=fg, weight=ft.FontWeight.W_700),
            ], spacing=8, tight=True, alignment=ft.MainAxisAlignment.CENTER),
            on_click=_mk_theme_handler(page, navigate, target),
            expand=True,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: (P.BRAND if active else "transparent"),
                    ft.ControlState.HOVERED: (P.BRAND if active else P.SURFACE_3),
                },
                shape=ft.RoundedRectangleBorder(radius=100),
                padding=ft.Padding(left=14, right=14, top=11, bottom=11),
            ),
        )
    return ft.Container(
        ft.Row([
            seg("Light", ft.Icons.LIGHT_MODE_ROUNDED, False),
            seg("Dark",  ft.Icons.DARK_MODE_ROUNDED,  True),
        ], spacing=6),
        bgcolor=P.SURFACE_2, border_radius=100, padding=6,
    )

def big_header(caption, title, page, navigate, trailing=None):
    tr = trailing if trailing is not None else theme_icon_button(page, navigate)
    return ft.Row([
        ft.Column([
            T(caption.upper(), size=11, color=P.MUTED, weight=ft.FontWeight.W_700),
            ft.Container(height=3),
            D(title, size=28, color=P.TEXT),
        ], spacing=0, expand=True),
        ft.Container(width=10),
        tr,
    ], vertical_alignment=ft.CrossAxisAlignment.START)
# ═══════════════════════════════════════════════════════════════════════════════
# NAV BAR
# ═══════════════════════════════════════════════════════════════════════════════
def build_nav(selected_index, on_change):
    bar = ft.NavigationBar(
        selected_index=selected_index,
        on_change=on_change,
        bgcolor=P.NAV_BG,
        indicator_color=P.NAV_INDICATOR,
        indicator_shape=ft.RoundedRectangleBorder(radius=14),
        shadow_color="transparent",
        label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED,     selected_icon=ft.Icons.HOME_ROUNDED,     label="Home"),
            ft.NavigationBarDestination(icon=ft.Icons.HISTORY_OUTLINED,  selected_icon=ft.Icons.HISTORY_ROUNDED,  label="History"),
            ft.NavigationBarDestination(icon=ft.Icons.INSIGHTS_OUTLINED, selected_icon=ft.Icons.INSIGHTS_ROUNDED, label="Analytics"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS_ROUNDED, label="Settings"),
            ft.NavigationBarDestination(icon=ft.Icons.INFO_OUTLINED,     selected_icon=ft.Icons.INFO_ROUNDED,     label="About"),
        ],
    )
    return ft.Container(
        ft.Column([ft.Container(height=1, bgcolor=P.BORDER), bar], spacing=0),
        bgcolor=P.NAV_BG,
    )
# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN: HOME
# ═══════════════════════════════════════════════════════════════════════════════
def build_home(page, navigate):
    fp = state.file_picker

    btn_ref    = ft.Ref[ft.Button]()
    status_ref = ft.Ref[ft.Text]()
    halo_ref   = ft.Ref[ft.Container]()
    anim       = {"on": False}

    HOME_BOX = 190

    async def _pulse():
        anim["on"] = True
        t = 0.0
        while anim["on"]:
            if halo_ref.current is None:
                break
            t += 1
            f = 0.5 + 0.5 * math.sin(t * 0.35)
            sz = 150 + 30 * f
            halo_ref.current.width = sz
            halo_ref.current.height = sz
            page.update()
            await asyncio.sleep(0.05)

    async def pick_file(_):
        btn_ref.current.disabled = True
        page.update()

        files = await fp.pick_files(
            dialog_title="Select Audio File",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["wav", "mp3", "ogg", "flac", "m4a", "aac"],
        )

        if not files:
            btn_ref.current.disabled = False
            status_ref.current.value = "No file selected."
            status_ref.current.color = P.ON_BRAND_MUTED
            page.update()
            return

        f = files[0]
        state.current_file = f.path
        status_ref.current.value = f"Analyzing  {f.name}"
        status_ref.current.color = P.ON_BRAND
        page.update()
        page.run_task(_pulse)

        loop = asyncio.get_event_loop()
        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result, duration = await loop.run_in_executor(
                    pool, _analyze_with_duration, f.path or f.name
                )
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            record = {
                "filename":   f.name,
                "audio_type": result["audio_type"],
                "language":   result.get("language"),
                "duration":   duration,
                "timestamp":  ts,
                "filepath":   f.path,   # store path for player
            }
            state.history_mgr.add(record)
            state.last_result = record
            anim["on"] = False
            btn_ref.current.disabled = False
            page.update()
            await navigate("result")
        except Exception as ex:
            anim["on"] = False
            btn_ref.current.disabled = False
            status_ref.current.value = f"Error: {ex}"
            status_ref.current.color = "#FFDAD9"
            page.update()

    # pipeline status pill
    if _PIPELINE_READY:
        pill = status_pill("SVM + Whisper models loaded", P.OK)
    else:
        pill = status_pill("Models not found — demo mode", P.WARN)

    # signature visual: breathing halo behind a white ring, on the blue hero
    visual = ft.Stack([
        _center_layer(ft.Container(
            ref=halo_ref, width=150, height=150, border_radius=200,
            bgcolor=HERO_TRACK,
            animate=ft.Animation(160, ft.AnimationCurve.EASE_IN_OUT),
        ), HOME_BOX),
        _center_layer(ring(
            ft.Icons.GRAPHIC_EQ_ROUNDED, P.WHITE, P.BRAND, P.WHITE,
            size=112, stroke=8, icon_size=42,
        ), HOME_BOX),
    ], width=HOME_BOX, height=HOME_BOX)

    hero = ft.Container(
        ft.Column([
            visual,
            ft.Container(height=18),
            D("Analyze a sound", size=22, color=P.ON_BRAND, align=ft.TextAlign.CENTER),
            ft.Container(height=6),
            T("WAV · MP3 · OGG · FLAC · M4A · AAC",
              size=12, color=P.ON_BRAND_MUTED, align=ft.TextAlign.CENTER),
            ft.Container(height=22),
            pill_button("Choose audio file", ft.Icons.FOLDER_OPEN_ROUNDED,
                        pick_file, kind="onbrand", ref=btn_ref),
            ft.Container(height=12),
            ft.Text(
                ref=status_ref, value="No file selected yet",
                size=12, color=P.ON_BRAND_MUTED,
                text_align=ft.TextAlign.CENTER, font_family=BODY_FONT,
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
        bgcolor=P.BRAND, border_radius=28,
        padding=ft.Padding(left=22, right=22, top=28, bottom=28),
    )

    # recent
    recent = state.history_mgr.records[:4]
    if recent:
        rows = []
        for r in recent:
            sub = r["audio_type"] + (f" · {r['language']}" if r.get("language") else "")
            rows.append(list_row(
                _type_icon(r["audio_type"]), _type_color(r["audio_type"]),
                _type_soft(r["audio_type"]), r["filename"], subtitle=sub,
                trailing=chip(r["audio_type"], _type_color(r["audio_type"]),
                              _type_soft(r["audio_type"])),
            ))
        recent_section = ft.Column([section_title("Recent"), group(rows)], spacing=10)
    else:
        recent_section = ft.Column([
            section_title("Recent"),
            empty_state(ft.Icons.GRAPHIC_EQ_ROUNDED, "Nothing analyzed yet",
                        "Your analyses will appear here."),
        ], spacing=10)

    return ft.Column([
        big_header("On-device audio AI", "Audio Classifier", page, navigate),
        pill,
        hero,
        recent_section,
    ], spacing=18, scroll=ft.ScrollMode.AUTO, expand=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN: RESULT
# ═══════════════════════════════════════════════════════════════════════════════
def build_result(page, navigate):
    async def _go_home(_):
        await navigate("home")

    r = state.last_result
    if not r:
        return ft.Column([
            D("No result yet", size=22, color=P.TEXT),
            pill_button("Go home", ft.Icons.HOME_ROUNDED, _go_home),
        ], spacing=20)

    atype    = r["audio_type"]
    col      = _type_color(atype)
    soft     = _type_soft(atype)
    lang     = r.get("language") or "N/A"
    has_lang = lang != "N/A"
    fpath    = r.get("filepath") or state.current_file or ""

    top = ft.Row([
        back_btn(_go_home),
        D("Result", size=22, color=P.TEXT),
        ft.Container(expand=True),
        theme_icon_button(page, navigate),
    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    file_row = ft.Row([
        ft.Icon(ft.Icons.AUDIO_FILE_ROUNDED, color=P.FAINT, size=15),
        T(r.get("filename", "Unknown file"), size=13, color=P.TEXT_2, weight=ft.FontWeight.W_500),
    ], spacing=8)

    hero = ft.Container(
        ft.Column([
            ring(_type_icon(atype), col, soft, col, size=124, stroke=11, icon_size=46),
            ft.Container(height=16),
            T("DETECTED", size=11, color=P.MUTED, weight=ft.FontWeight.W_700, align=ft.TextAlign.CENTER),
            ft.Container(height=4),
            D(atype, size=34, color=P.TEXT, align=ft.TextAlign.CENTER),
            ft.Container(height=12),
            chip(atype, col, soft),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
        bgcolor=P.SURFACE, border_radius=28,
        padding=ft.Padding(left=20, right=20, top=28, bottom=28),
        border=ft.Border.all(1, P.BORDER),
        alignment=ft.alignment.Alignment(0, 0),
    )

    info = group([
        list_row(ft.Icons.LANGUAGE_ROUNDED,
                 P.SPEECH if has_lang else P.MUTED,
                 P.SPEECH_SOFT if has_lang else P.SURFACE_2,
                 "Language", value=(lang if has_lang else "Not speech")),
        list_row(ft.Icons.TIMER_OUTLINED, P.BRAND, P.BRAND_SOFT,
                 "Duration", value=r.get("duration", "N/A")),
        list_row(ft.Icons.SCHEDULE_ROUNDED, P.TEXT_2, P.SURFACE_2,
                 "Analyzed", value=r.get("timestamp", "N/A")),
    ])

    # ── in-app audio player ───────────────────────────────────────────────────
    # ROOT CAUSE of all previous failures:
    #   play()/pause()/resume()/seek() all use _invoke_method which sends a
    #   message to Flutter and waits 30s for an ACK. The ACK never comes
    #   because the native audioplayers plugin's method channel is not active
    #   until the control is mounted with a real src at creation time.
    #
    # THE FIX: never call play()/pause()/resume() at all.
    #   - Use autoplay=True so the file plays the moment the control mounts.
    #   - To "pause": set volume=0 (instant, no round-trip needed).
    #   - To "resume": set volume=1 (instant, no round-trip needed).
    #   - To seek: we use a fresh Audio control (simplest, most reliable).
    #   - Track position via on_position_change; duration via on_duration_change.
    #   - e.duration  → ft.Duration object → .in_milliseconds
    #   - e.position  → plain int (ms) already

    play_icon_ref = ft.Ref[ft.Icon]()
    seek_ref      = ft.Ref[ft.Slider]()
    elapsed_ref   = ft.Ref[ft.Text]()
    total_ref     = ft.Ref[ft.Text]()
    status_ref    = ft.Ref[ft.Text]()

    seek_dragging = {"v": False}
    total_ms      = {"v": 0}
    # paused = muted via volume=0; playing = volume=1
    paused        = {"v": False}

    def _fmt_ms(ms):
        if not ms or ms < 0:
            return "0:00"
        total_s = int(ms) // 1000
        m, s = divmod(total_s, 60)
        return f"{m}:{s:02d}"

    def _set_status(text, color=None):
        if status_ref.current:
            status_ref.current.value = text
            status_ref.current.color = color or P.MUTED
            page.update()

    def _set_icon(is_playing: bool):
        state.is_playing = is_playing
        if play_icon_ref.current:
            play_icon_ref.current.icon = (
                ft.Icons.PAUSE_CIRCLE_ROUNDED if is_playing
                else ft.Icons.PLAY_CIRCLE_ROUNDED
            )
        page.update()

    def _current_player() -> fa.Audio | None:
        """Return the Audio service currently in page.services, if any."""
        for svc in list(page.services):
            if isinstance(svc, fa.Audio):
                return svc
        return None

    def _remove_player():
        """Remove any existing Audio services cleanly."""
        to_remove = [s for s in list(page.services) if isinstance(s, fa.Audio)]
        for s in to_remove:
            page.services.remove(s)
        if to_remove:
            page.update()

    def _make_player(path: str) -> fa.Audio:
        """Create a fresh Audio service with autoplay=True for the given path."""
        p = fa.Audio(
            src=os.path.abspath(path),
            autoplay=True,
            volume=1.0,
            release_mode=fa.ReleaseMode.STOP,
        )
        p.on_state_change    = _on_state_change
        p.on_duration_change = _on_duration_change
        p.on_position_change = _on_position_change
        return p

    async def _on_state_change(e):
        st = e.state
        if st == fa.AudioState.PLAYING:
            if not paused["v"]:
                _set_icon(True)
                _set_status("Playing")
        elif st == fa.AudioState.PAUSED:
            _set_icon(False)
            _set_status("Paused")
        elif st in (fa.AudioState.COMPLETED, fa.AudioState.STOPPED):
            _set_icon(False)
            state.is_playing = False
            state.playing_path = None
            paused["v"] = False
            if st == fa.AudioState.COMPLETED:
                if seek_ref.current:
                    seek_ref.current.value = 0
                if elapsed_ref.current:
                    elapsed_ref.current.value = "0:00"
                page.update()

    async def _on_duration_change(e):
        try:
            ms = e.duration.in_milliseconds
        except AttributeError:
            ms = int(e.duration) if e.duration else 0
        total_ms["v"] = ms
        if seek_ref.current:
            seek_ref.current.max = max(ms, 1)
        if total_ref.current:
            total_ref.current.value = _fmt_ms(ms)
        page.update()

    async def _on_position_change(e):
        if seek_dragging["v"] or paused["v"]:
            return
        pos = int(e.position)
        if seek_ref.current:
            seek_ref.current.value = min(pos, max(seek_ref.current.max, 1))
        if elapsed_ref.current:
            elapsed_ref.current.value = _fmt_ms(pos)
        page.update()

    async def _toggle_play(_):
        if not fpath or not os.path.exists(fpath):
            _set_status("File not found", color=P.ERR)
            return

        player = _current_player()

        if player and state.playing_path == fpath:
            if paused["v"]:
                # Un-mute to resume
                player.volume = 1.0
                page.update()
                paused["v"] = False
                _set_icon(True)
                _set_status("Playing")
            else:
                # Mute to "pause" — no invoke_method needed
                player.volume = 0.0
                page.update()
                paused["v"] = True
                _set_icon(False)
                _set_status("Paused")
            return

        # New file — remove old player, mount fresh one with autoplay
        _remove_player()
        paused["v"] = False
        state.playing_path = fpath
        state.is_playing = True
        new_player = _make_player(fpath)
        page.services.append(new_player)
        page.update()
        _set_icon(True)
        _set_status("Playing")

    async def _on_seek_start(_):
        seek_dragging["v"] = True

    async def _on_seek_end(e):
        seek_dragging["v"] = False
        target_ms = int(e.control.value)
        if elapsed_ref.current:
            elapsed_ref.current.value = _fmt_ms(target_ms)
            page.update()
        # Restart playback from target position using a fresh player
        if state.playing_path == fpath:
            player = _current_player()
            if player:
                _remove_player()
                new_player = _make_player(fpath)
                # Can't seek at mount time, but can use play(position=...) — skip for now
                # Simplest: just restart from beginning if user seeks
                page.services.append(new_player)
                page.update()

    is_active   = state.is_playing and state.playing_path == fpath
    has_audio   = bool(fpath and os.path.exists(fpath))
    init_total  = total_ms["v"]

    play_icon_btn = ft.IconButton(
        icon=ft.Icons.PAUSE_CIRCLE_ROUNDED if is_active else ft.Icons.PLAY_CIRCLE_ROUNDED,
        icon_color=col, icon_size=44,
        ref=play_icon_ref,
        on_click=_toggle_play,
        style=ft.ButtonStyle(padding=0),
    )

    seek_bar = ft.Slider(
        ref=seek_ref,
        value=0, min=0, max=max(init_total, 1),
        active_color=col, inactive_color=P.SURFACE_2, thumb_color=col,
        on_change_start=_on_seek_start,
        on_change_end=_on_seek_end,
    )

    player_card = card(
        ft.Column([
            ft.Row([
                play_icon_btn,
                ft.Column([
                    T("Now playing", size=12, color=P.MUTED, weight=ft.FontWeight.W_600),
                    T(r.get("filename", "Audio"), size=14, color=P.TEXT,
                      weight=ft.FontWeight.W_700, font="Manrope"),
                ], spacing=2, expand=True),
            ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(height=4),
            seek_bar,
            ft.Row([
                ft.Text("0:00", ref=elapsed_ref, size=11, color=P.MUTED, font_family=BODY_FONT),
                ft.Container(expand=True),
                ft.Text(_fmt_ms(init_total), ref=total_ref, size=11, color=P.MUTED, font_family=BODY_FONT),
            ]),
            ft.Text("", ref=status_ref, size=11, color=P.MUTED, font_family=BODY_FONT),
        ], spacing=2),
        pad=ft.Padding(left=16, right=16, top=14, bottom=10),
    ) if has_audio else ft.Column([])

    # ── Profanity detection ───────────────────────────────────────────────────
    profanity_card_ref = ft.Ref[ft.Column]()
    profanity_btn_ref  = ft.Ref[ft.Container]()

    # Category → colour mapping
    _PROF_COLORS = {
        "toxic":            "#E5484D",
        "obscene":          "#E5484D",
        "insult":           "#E5484D",
        "threat":           "#E08A00",
        "identity_attack":  "#E08A00",
        "sexual_explicit":  "#E5484D",
        "Safe":             "#12A150",
        "unavailable":      P.MUTED,
    }

    def _score_bar(label: str, score: float) -> ft.Control:
        pct   = max(0.0, min(1.0, score))
        color = P.ERR if pct >= 0.70 else (P.WARN if pct >= 0.40 else P.OK)
        # expand requires bool or int — render bar as a Stack instead
        filled_w = max(4, int(pct * 260))  # 260 ≈ card inner width
        return ft.Column([
            ft.Row([
                T(label, size=11, color=P.TEXT_2),
                ft.Container(expand=True),
                T(f"{pct*100:.1f}%", size=11, color=color, weight=ft.FontWeight.W_700),
            ]),
            ft.Stack([
                ft.Container(height=4, bgcolor=P.SURFACE_2, border_radius=4, expand=True),
                ft.Container(width=filled_w, height=4, bgcolor=color, border_radius=4),
            ], height=4),
        ], spacing=4)

    def _build_profanity_result(pr: dict) -> ft.Control:
        is_profane = pr.get("is_profane", False)
        category   = pr.get("category", "Safe")
        score_pct  = pr.get("score", 0.0)
        all_scores = pr.get("all_scores", {})
        err        = pr.get("error")

        badge_color = _PROF_COLORS.get(category, P.MUTED)
        verdict     = "⚠  Profanity Detected" if is_profane else "✓  Clean Audio"
        verdict_col = P.ERR if is_profane else P.OK

        rows = [
            ft.Row([
                ft.Icon(
                    ft.Icons.WARNING_ROUNDED if is_profane else ft.Icons.CHECK_CIRCLE_ROUNDED,
                    color=verdict_col, size=18,
                ),
                T(verdict, size=15, color=verdict_col, weight=ft.FontWeight.W_700),
            ], spacing=8),
        ]

        if err:
            rows.append(T(f"Error: {err}", size=11, color=P.MUTED))
        else:
            rows += [
                ft.Container(height=4),
                ft.Row([
                    T("Category", size=12, color=P.MUTED),
                    ft.Container(expand=True),
                    ft.Container(
                        T(category, size=11, color=badge_color, weight=ft.FontWeight.W_700),
                        bgcolor=badge_color + "22",
                        border_radius=20,
                        padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                    ),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    T("Confidence", size=12, color=P.MUTED),
                    ft.Container(expand=True),
                    T(f"{score_pct:.1f}%", size=12, color=P.TEXT, weight=ft.FontWeight.W_700),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                divider(),
                T("LABEL SCORES", size=10, color=P.MUTED, weight=ft.FontWeight.W_700),
                ft.Container(height=2),
                *[_score_bar(lbl, sc) for lbl, sc in all_scores.items()],
            ]

        return card(ft.Column([
            ft.Row([
                icon_square(ft.Icons.SHIELD_ROUNDED, P.ERR if is_profane else P.OK,
                            (P.ERR if is_profane else P.OK) + "22"),
                T("Content Safety", size=16, color=P.TEXT, weight=ft.FontWeight.W_700),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            divider(),
            *rows,
        ], spacing=8))

    async def _run_profanity(_):
        # Only works on Speech clips that have a filepath
        if not fpath or not os.path.exists(fpath):
            return
        if not _PROFANITY_READY:
            return

        # Disable button while running
        if profanity_btn_ref.current:
            profanity_btn_ref.current.opacity = 0.5
            profanity_btn_ref.current.disabled = True
            page.update()

        loop = asyncio.get_event_loop()
        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                # translate_to_english then check_profanity
                from audio_pipeline import translate_to_english as _translate
                translated = await loop.run_in_executor(pool, _translate, fpath)
                pr = await loop.run_in_executor(pool, _check_profanity, translated)
        except Exception as ex:
            pr = {
                "is_profane": False, "category": "unavailable",
                "score": 0.0, "all_scores": {}, "error": str(ex),
            }

        if profanity_card_ref.current is not None:
            profanity_card_ref.current.controls = [_build_profanity_result(pr)]
            profanity_card_ref.current.visible  = True

        if profanity_btn_ref.current:
            profanity_btn_ref.current.opacity  = 1.0
            profanity_btn_ref.current.disabled = False

        page.update()

    # Only show profanity button for Speech clips
    show_profanity_btn = (atype == "Speech") and bool(fpath) and _PROFANITY_READY

    profanity_btn = ft.Container(
        ref=profanity_btn_ref,
        content=ft.Row([
            ft.Icon(ft.Icons.SHIELD_ROUNDED, color=P.ON_BRAND, size=18),
            T("Check Content Safety", size=14, color=P.ON_BRAND, weight=ft.FontWeight.W_700),
        ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
        on_click=_run_profanity,
        bgcolor=P.BRAND,
        border_radius=100,
        padding=ft.Padding(left=20, right=20, top=14, bottom=14),
        expand=True,
        animate_opacity=200,
    ) if show_profanity_btn else ft.Column([])

    profanity_result_area = ft.Column(
        ref=profanity_card_ref,
        controls=[],
        visible=False,
    )

    return ft.Column([
        top,
        file_row,
        hero,
        player_card,
        info,
        profanity_btn,
        profanity_result_area,
        ft.Container(height=2),
        pill_button("Analyze another", ft.Icons.ADD_ROUNDED, _go_home, expand=True),
    ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)
# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN: HISTORY
# ═══════════════════════════════════════════════════════════════════════════════
def build_history(page, navigate):
    records = state.history_mgr.records
    header = big_header(f"{len(records)} analyses", "History", page, navigate)

    if records:
        rows = []
        for r in records:
            sub = r["audio_type"]
            if r.get("language"):
                sub += f" · {r['language']}"
            if r.get("timestamp"):
                sub += f" · {r['timestamp']}"
            rows.append(list_row(
                _type_icon(r["audio_type"]), _type_color(r["audio_type"]),
                _type_soft(r["audio_type"]), r.get("filename", "unknown"),
                subtitle=sub,
                trailing=chip(r["audio_type"], _type_color(r["audio_type"]),
                              _type_soft(r["audio_type"])),
            ))
        body = group(rows)
    else:
        body = empty_state(ft.Icons.HISTORY_ROUNDED, "No history yet",
                           "Analyze an audio file to see it here.")

    return ft.Column([header, body], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)
# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN: ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════
def build_analytics(page, navigate):
    s = state.history_mgr.stats()
    total, speech, music, noise = s["total"], s["speech"], s["music"], s["noise"]

    tiles = ft.Column([
        ft.Row([
            stat_tile(total, "Total scans", P.BRAND, P.BRAND_SOFT,
                      ft.Icons.GRAPHIC_EQ_ROUNDED, brand=True),
            stat_tile(speech, "Speech", P.SPEECH, P.SPEECH_SOFT, ft.Icons.MIC_ROUNDED),
        ], spacing=12),
        ft.Row([
            stat_tile(music, "Music", P.MUSIC, P.MUSIC_SOFT, ft.Icons.MUSIC_NOTE_ROUNDED),
            stat_tile(noise, "Noise", P.NOISE, P.NOISE_SOFT, ft.Icons.WAVES_ROUNDED),
        ], spacing=12),
    ], spacing=12)

    seg = []
    for cnt, clr in [(speech, P.SPEECH), (music, P.MUSIC), (noise, P.NOISE)]:
        if cnt > 0:
            seg.append(ft.Container(expand=cnt, height=16, bgcolor=clr, border_radius=8))
    bar = ft.Row(seg, spacing=4) if seg else ft.Container(height=16, bgcolor=P.SURFACE_2, border_radius=8)

    def leg(label, cnt, clr):
        return ft.Row([
            ft.Container(width=8, height=8, border_radius=4, bgcolor=clr),
            T(label, size=12, color=P.MUTED),
            T(str(cnt), size=12, color=clr, weight=ft.FontWeight.W_700),
        ], spacing=6, tight=True)

    dist_card = card(ft.Column([
        T("TYPE DISTRIBUTION", size=11, color=P.MUTED, weight=ft.FontWeight.W_700),
        ft.Container(height=12),
        bar,
        ft.Container(height=14),
        ft.Row([leg("Speech", speech, P.SPEECH), leg("Music", music, P.MUSIC),
                leg("Noise", noise, P.NOISE)], spacing=18, wrap=True, run_spacing=8),
    ], spacing=0))

    lang_items = sorted(s["lang_dist"].items(), key=lambda x: -x[1])[:6]
    lang_rows = (
        [ft.Row([
            T(lang, size=14, color=P.TEXT_2),
            ft.Container(expand=True),
            chip(str(cnt), P.SPEECH, P.SPEECH_SOFT),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER) for lang, cnt in lang_items]
        if lang_items else [T("No speech detected yet", size=14, color=P.MUTED)]
    )
    lang_card = card(ft.Column([
        T("LANGUAGE BREAKDOWN", size=11, color=P.MUTED, weight=ft.FontWeight.W_700),
        *lang_rows,
    ], spacing=12))

    return ft.Column([
        big_header("Insights", "Analytics", page, navigate),
        tiles, dist_card, lang_card,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)
# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN: SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════
def build_settings(page, navigate):

    async def _export(_):
        content = state.history_mgr.export()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fpath = os.path.join(APP_DIR, f"audio_history_{ts}.txt")
        try:
            with open(fpath, "w") as f:
                f.write(content)
            page.show_dialog(ft.SnackBar(
                ft.Text(f"Saved to {fpath}", color=P.ON_BRAND), bgcolor=P.BRAND))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(
                ft.Text(f"Export failed: {ex}", color=P.WHITE), bgcolor=P.ERR))
        page.update()

    async def _clear(_):
        async def _confirm(e):
            state.history_mgr.clear()
            page.pop_dialog()
            page.update()
            await navigate("settings")

        async def _cancel(e):
            page.pop_dialog()
            page.update()

        dlg = ft.AlertDialog(
            title=D("Clear all history?", size=18, color=P.TEXT),
            content=T("This cannot be undone.", size=13, color=P.TEXT_2),
            actions=[
                ft.TextButton("Cancel", on_click=_cancel, style=ft.ButtonStyle(color=P.MUTED)),
                ft.TextButton("Delete all", on_click=_confirm, style=ft.ButtonStyle(color=P.ERR)),
            ],
            bgcolor=P.SURFACE,
            shape=ft.RoundedRectangleBorder(radius=20),
        )
        page.show_dialog(dlg)
        page.update()

    appearance = ft.Column([
        section_title("Appearance"),
        card(ft.Column([
            ft.Row([
                icon_square(ft.Icons.PALETTE_OUTLINED, P.BRAND, P.BRAND_SOFT),
                ft.Column([
                    T("Theme", size=15, color=P.TEXT, weight=ft.FontWeight.W_700),
                    T("Choose light or dark", size=12, color=P.MUTED),
                ], spacing=2, expand=True),
            ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(height=14),
            theme_segment(page, navigate),
        ], spacing=0), pad=16),
    ], spacing=10)

    data = ft.Column([
        section_title("Data"),
        group([
            list_row(ft.Icons.DOWNLOAD_ROUNDED, P.BRAND, P.BRAND_SOFT,
                     "Export history", "Save analyses to a text file",
                     trailing=chevron_btn(_export, P.MUTED)),
            list_row(ft.Icons.DELETE_OUTLINE_ROUNDED, P.ERR, P.ERR_SOFT,
                     "Clear history", "Remove all stored analyses",
                     trailing=chevron_btn(_clear, P.ERR)),
        ]),
    ], spacing=10)

    return ft.Column([
        big_header("Preferences", "Settings", page, navigate),
        appearance, data,
    ], spacing=18, scroll=ft.ScrollMode.AUTO, expand=True)
# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN: ABOUT
# ═══════════════════════════════════════════════════════════════════════════════
def build_about(page, navigate):
    hero = ft.Container(
        ft.Column([
            ring(ft.Icons.GRAPHIC_EQ_ROUNDED, P.WHITE, P.BRAND, P.WHITE,
                 size=92, stroke=7, icon_size=34),
            ft.Container(height=16),
            D("Audio Classifier", size=24, color=P.ON_BRAND, align=ft.TextAlign.CENTER),
            ft.Container(height=4),
            T(f"v{APP_VERSION} · Speech / Music / Noise",
              size=12, color=P.ON_BRAND_MUTED, align=ft.TextAlign.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
        bgcolor=P.BRAND, border_radius=28,
        padding=ft.Padding(left=20, right=20, top=28, bottom=30),
        alignment=ft.alignment.Alignment(0, 0),
    )

    svm = spec_card("SVM Classifier", {
        "Purpose":  "Audio type classification",
        "Classes":  "Speech · Music · Noise",
        "Features": "57 (MFCC, Chroma, Spectral)",
        "Dataset":  "MUSAN", "Kernel": "RBF",
    }, P.BRAND, P.BRAND_SOFT, ft.Icons.MODEL_TRAINING_ROUNDED)

    whisper = spec_card("Whisper", {
        "Purpose":    "Language detection",
        "Model size": "Small",
        "Languages":  "10 supported",
        "Method":     "Log-mel spectrogram",
    }, P.MUSIC, P.MUSIC_SOFT, ft.Icons.TRANSLATE_ROUNDED)

    langs = card(ft.Column([
        T("SUPPORTED LANGUAGES", size=11, color=P.MUTED, weight=ft.FontWeight.W_700),
        ft.Container(height=10),
        ft.Row(wrap=True, spacing=8, run_spacing=8,
               controls=[chip(l, P.TEXT_2, P.SURFACE_2) for l in LANGUAGES]),
    ], spacing=0))

    about = ft.Column([
        section_title("About"),
        group([
            list_row(ft.Icons.INFO_OUTLINE_ROUNDED, P.TEXT_2, P.SURFACE_2,
                     "Version", "Audio Classifier",
                     trailing=chip(f"v{APP_VERSION}", P.TEXT_2, P.SURFACE_2)),
        ]),
    ], spacing=10)

    return ft.Column([
        big_header("Audio intelligence", "About", page, navigate),
        hero, svm, whisper, langs, about,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)
# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def _make_theme(pal):
    return ft.Theme(
        color_scheme_seed=pal.BRAND,
        font_family=BODY_FONT,
        navigation_bar_theme=ft.NavigationBarTheme(
            label_text_style={
                ft.ControlState.DEFAULT: ft.TextStyle(
                    size=11, color=pal.NAV_LABEL,
                    weight=ft.FontWeight.W_600, font_family=BODY_FONT),
                ft.ControlState.SELECTED: ft.TextStyle(
                    size=11, color=pal.NAV_LABEL_SEL,
                    weight=ft.FontWeight.W_700, font_family=BODY_FONT),
            },
        ),
    )
async def main(page: ft.Page):
    page.title   = "Audio Classifier"
    page.padding = 0
    page.fonts   = {"Manrope": MANROPE_URL}

    page.theme      = _make_theme(LIGHT_PAL)
    page.dark_theme = _make_theme(DARK_PAL)

    _load_settings()
    set_palette(IS_DARK)
    apply_page_theme(page)

    state.file_picker = ft.FilePicker()
    page.services.append(state.file_picker)
    page.update()

    current_nav = {"v": 0}

    SCREEN_MAP = {
        "home": 0, "history": 1, "analytics": 2,
        "settings": 3, "about": 4, "result": None,
    }

    builders = {
        "home":      build_home,
        "result":    build_result,
        "history":   build_history,
        "analytics": build_analytics,
        "settings":  build_settings,
        "about":     build_about,
    }

    async def navigate(screen: str):
        state.current_screen = screen
        idx = SCREEN_MAP.get(screen, 0)
        if idx is not None:
            current_nav["v"] = idx
        content = builders.get(screen, build_home)(page, navigate)
        page.controls.clear()
        page.controls.append(
            ft.Column([
                ft.Container(
                    content=content, expand=True,
                    padding=ft.Padding(left=20, right=20, top=16, bottom=10),
                ),
                build_nav(current_nav["v"], on_nav_change),
            ], expand=True, spacing=0)
        )
        page.update()

    async def on_nav_change(e):
        idx_map = {0: "home", 1: "history", 2: "analytics", 3: "settings", 4: "about"}
        await navigate(idx_map.get(e.control.selected_index, "home"))

    await navigate("home")
ft.run(main)
