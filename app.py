import streamlit as st
import sqlite3
import pandas as pd
import io
import os
import time
import random
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import json

try:
    from pypinyin import pinyin, Style
    HAS_PINYIN = True
except ImportError:
    HAS_PINYIN = False

try:
    from gtts import gTTS
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

try:
    from hanzi_chaizi import HanziChaizi
    _chaizi = HanziChaizi()
    HAS_CHAIZI = True
except Exception:
    HAS_CHAIZI = False
    _chaizi = None

try:
    import eng_to_ipa as _ipa_lib
    HAS_ENG_IPA = True
except ImportError:
    HAS_ENG_IPA = False
    _ipa_lib = None


st.set_page_config(
    page_title="Flashcard Pro",
    page_icon="🎴",
    layout="centered",
    initial_sidebar_state="expanded"
)


st.markdown("""
<style>
html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; font-size: 17px; }
h1 { font-size: 2.4rem; font-weight: 800; }
h2 { font-size: 1.7rem; font-weight: 700; }
.stTextInput input, .stTextArea textarea, .stSelectbox select {
    font-size: 17px; padding: 12px 14px; border-radius: 10px;
}
.stTextInput label, .stTextArea label, .stSelectbox label {
    font-size: 16px; font-weight: 600; color: #cbd5e1;
}
.stButton > button {
    font-size: 16px; font-weight: 600; padding: 12px 20px; border-radius: 12px;
}
section[data-testid="stSidebar"] {
    width: 320px;
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}
section[data-testid="stSidebar"] * { font-size: 17px; }
section[data-testid="stSidebar"] h2 {
    font-size: 1.4rem;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
section[data-testid="stSidebar"] [role="radiogroup"] label {
    padding: 12px 14px; border-radius: 10px; margin-bottom: 4px;
}
.stApp {
    background: linear-gradient(-45deg, #0a0a14, #131b2e, #0f172a, #1a0f2e, #0a0a14);
    background-size: 400% 400%;
}
div[data-testid="stExpander"] {
    border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 12px;
    background: rgba(30, 41, 59, 0.5); margin-bottom: 10px;
}
div[data-testid="stMetric"] {
    background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 12px; padding: 16px;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 2rem; font-weight: 700;
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.flashcard-word {
    text-align: center; color: #60a5fa; font-size: 3.5rem; font-weight: 800; margin: 20px 0;
}
.practice-word {
    text-align: center; color: #34d399; font-size: 2.5rem; font-weight: 800; margin: 20px 0;
}
.wotd-card {
    padding: 20px; border-radius: 16px;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(236, 72, 153, 0.15));
    border: 1px solid rgba(99, 102, 241, 0.3);
    text-align: center; margin: 15px 0;
}
.wotd-word {
    font-size: 2.2rem; font-weight: 800;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
}
.streak-fire {
    font-size: 2rem; text-align: center; padding: 10px;
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(249, 115, 22, 0.2));
    border-radius: 12px; border: 1px solid rgba(249, 115, 22, 0.3);
}
[data-testid="stHeader"] { background: rgba(10, 10, 20, 0.6); }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 10px; }
@media (max-width: 768px) {
    [data-testid="stHeader"] { height: 52px; background: rgba(10, 10, 20, 0.95); }
    [data-testid="stHeader"] button { min-width: 46px; min-height: 46px; color: #60a5fa; }
    section[data-testid="stSidebar"] { width: 82vw; min-width: 82vw; }
    .main .block-container { padding-left: 0.8rem; padding-right: 0.8rem; max-width: 100%; }
    .flashcard-word { font-size: 2.8rem; }
    .practice-word { font-size: 1.9rem; }
    .stButton > button { min-height: 50px; }
    .stTextInput input, .stTextArea textarea, .stSelectbox select { min-height: 48px; }
}
</style>
""", unsafe_allow_html=True)


ARPABET_TO_IPA = {
    'AA': 'ɑː', 'AE': 'æ', 'AH': 'ʌ', 'AO': 'ɔː', 'AW': 'aʊ', 'AY': 'aɪ',
    'B': 'b', 'CH': 'tʃ', 'D': 'd', 'DH': 'ð', 'EH': 'e', 'ER': 'ɜːr',
    'EY': 'eɪ', 'F': 'f', 'G': 'ɡ', 'HH': 'h', 'IH': 'ɪ', 'IY': 'iː',
    'JH': 'dʒ', 'K': 'k', 'L': 'l', 'M': 'm', 'N': 'n', 'NG': 'ŋ',
    'OW': 'oʊ', 'OY': 'ɔɪ', 'P': 'p', 'R': 'r', 'S': 's', 'SH': 'ʃ',
    'T': 't', 'TH': 'θ', 'UH': 'ʊ', 'UW': 'uː', 'V': 'v', 'W': 'w',
    'Y': 'j', 'Z': 'z', 'ZH': 'ʒ',
}


def arpabet_to_ipa(arpabet):
    if not arpabet or not isinstance(arpabet, str):
        return ""
    tokens = arpabet.split()
    parts = []
    for token in tokens:
        if not token:
            continue
        stress = ""
        if token[-1].isdigit():
            stress = {'0': '', '1': 'ˈ', '2': 'ˌ'}.get(token[-1], '')
            token = token[:-1]
        ipa = ARPABET_TO_IPA.get(token.upper(), "")
        if ipa:
            parts.append(stress + ipa)
    return "".join(parts)


RADICALS = {
    '一':'nhất','丨':'cổn','丶':'chủ','丿':'phiệt','乙':'ất','亅':'quyết',
    '二':'nhị','亠':'đầu','人':'nhân','亻':'nhân','儿':'nhi','入':'nhập',
    '八':'bát','冂':'quynh','冖':'mịch','冫':'băng','几':'kỷ','凵':'khảm',
    '刀':'đao','刂':'đao','力':'lực','勹':'bao','匕':'chủy','匚':'phương',
    '匸':'hệ','十':'thập','卜':'bốc','卩':'tiết','厂':'hán','厶':'khư',
    '又':'hựu','口':'khẩu','囗':'vi','土':'thổ','士':'sĩ','夂':'truy',
    '夕':'tịch','大':'đại','女':'nữ','子':'tử','宀':'miên','寸':'thốn',
    '小':'tiểu','尢':'uông','尸':'thi','屮':'triệt','山':'sơn','巛':'xuyên',
    '工':'công','己':'kỷ','巾':'cân','干':'can','幺':'yêu','广':'nghiễm',
    '廴':'dẫn','廾':'củng','弋':'dặc','弓':'cung','彐':'ký','彡':'sam',
    '彳':'xích','心':'tâm','忄':'tâm','戈':'qua','戶':'hộ','户':'hộ',
    '手':'thủ','扌':'thủ','支':'chi','攴':'phộc','攵':'phộc','文':'văn',
    '斗':'đẩu','斤':'cân','方':'phương','无':'vô','日':'nhật','曰':'viết',
    '月':'nguyệt','木':'mộc','欠':'khiếm','止':'chỉ','歹':'đãi','殳':'thù',
    '毋':'vô','比':'tỷ','毛':'mao','氏':'thị','气':'khí','水':'thủy',
    '氵':'thủy','氺':'thủy','火':'hỏa','灬':'hỏa','爪':'trảo','爫':'trảo',
    '父':'phụ','爻':'hào','爿':'tường','片':'phiến','牙':'nha','牛':'ngưu',
    '牜':'ngưu','犬':'khuyển','犭':'khuyển','玄':'huyền','玉':'ngọc',
    '王':'ngọc','瓜':'qua','瓦':'ngõa','甘':'cam','生':'sinh','用':'dụng',
    '田':'điền','疋':'nhã','疒':'nạch','癶':'bát','白':'bạch','皮':'bì',
    '皿':'mãnh','目':'mục','矛':'mâu','矢':'thỉ','石':'thạch','示':'thị',
    '礻':'thị','禸':'nhựu','禾':'hòa','穴':'huyệt','立':'lập','竹':'trúc',
    '⺮':'trúc','米':'mễ','糸':'mịch','纟':'mịch','缶':'phữu','网':'võng',
    '罒':'võng','羊':'dương','羽':'vũ','老':'lão','耂':'lão','而':'nhi',
    '耒':'lỗi','耳':'nhĩ','聿':'duật','肉':'nhục','臣':'thần','自':'tự',
    '至':'chí','臼':'cữu','舌':'thiệt','舛':'suyễn','舟':'chu','艮':'cấn',
    '色':'sắc','艸':'thảo','艹':'thảo','虍':'hổ','虫':'trùng','血':'huyết',
    '行':'hành','衣':'y','衤':'y','襾':'á','見':'kiến','见':'kiến',
    '角':'giác','言':'ngôn','讠':'ngôn','谷':'cốc','豆':'đậu','豕':'thỉ',
    '豸':'trãi','貝':'bối','贝':'bối','赤':'xích','走':'tẩu','足':'túc',
    '身':'thân','車':'xa','车':'xa','辛':'tân','辰':'thần','辵':'sước',
    '辶':'sước','邑':'ấp','阝':'phụ','酉':'dậu','釆':'biện','里':'lý',
    '金':'kim','钅':'kim','長':'trường','长':'trường','門':'môn','门':'môn',
    '阜':'phụ','隶':'lệ','隹':'chuy','雨':'vũ','青':'thanh','非':'phi',
    '面':'diện','革':'cách','韋':'vi','韦':'vi','韭':'cửu','音':'âm',
    '頁':'hiệt','页':'hiệt','風':'phong','风':'phong','飛':'phi','飞':'phi',
    '食':'thực','饣':'thực','首':'thủ','香':'hương','馬':'mã','马':'mã',
    '骨':'cốt','高':'cao','髟':'tiêu','鬥':'đấu','鬯':'sưởng','鬲':'cách',
    '鬼':'quỷ','魚':'ngư','鱼':'ngư','鳥':'điểu','鸟':'điểu','鹵':'lỗ',
    '鹿':'lộc','麥':'mạch','麦':'mạch','麻':'ma','黃':'hoàng','黄':'hoàng',
    '黍':'thử','黑':'hắc','鼓':'cổ','黽':'mãnh','黾':'mãnh','鼎':'đỉnh',
    '鼠':'thử','鼻':'tỵ','齊':'tề','齐':'tề','齒':'xỉ','齿':'xỉ',
    '龍':'long','龙':'long','龜':'quy','龟':'quy','龠':'thược',
    '丬':'tường','乛':'ất','龴':'ất',
}

RADICALS_LEFT = set('亻讠氵忄扌女木火土钅纟饣犭礻衤目田石王日月口山刂阝牜禾米虫马鱼鸟贝车歹斤寸戈方白立竹糸言金食馬鳥魚門車貝頁風')
RADICALS_TOP = set('宀艹竹雨疒亠广厂尸户穴罒气麻鹿彐')
RADICALS_BOTTOM = set('心灬皿儿廾大辶廴乙')
RADICALS_ENCLOSE = set('囗门門冂匚勹匸风几')

VARIANT_MAP = {
    '亻':'人','讠':'言','氵':'水','忄':'心','扌':'手','犭':'犬',
    '纟':'糸','饣':'食','钅':'金','礻':'示','衤':'衣','刂':'刀',
    '牜':'牛','爫':'爪','⺮':'竹','罒':'网','户':'戶',
}


def radical_label(ch):
    name = RADICALS.get(ch)
    origin = VARIANT_MAP.get(ch)
    if name:
        if origin:
            return f"Bộ {name} ({ch} → {origin})"
        return f"Bộ {name} ({ch})"
    return f"Thành phần ({ch})"


def _fallback_components(ch):
    if ch in RADICALS:
        return [ch]
    for r in RADICALS_ENCLOSE:
        if r in ch and r != ch:
            rest = ch.replace(r, '', 1)
            if rest in RADICALS:
                return [r, rest]
            return [r] + _fallback_components(rest)
    for r in RADICALS_LEFT:
        if r in ch and r != ch:
            rest = ch.replace(r, '', 1)
            if rest in RADICALS:
                return [r, rest]
            return [r] + _fallback_components(rest)
    for r in RADICALS_TOP:
        if r in ch and r != ch:
            rest = ch.replace(r, '', 1)
            if rest in RADICALS:
                return [r, rest]
            return [r] + _fallback_components(rest)
    for r in RADICALS_BOTTOM:
        if r in ch and r != ch:
            rest = ch.replace(r, '', 1)
            if rest in RADICALS:
                return [r, rest]
            return [r] + _fallback_components(rest)
    for r in RADICALS:
        if r != ch and r in ch:
            rest = ch.replace(r, '', 1)
            if rest in RADICALS:
                return [r, rest]
            return [r] + _fallback_components(rest)
    return [ch]


def decompose_char(ch):
    if not is_chinese(ch):
        return []
    if HAS_CHAIZI:
        try:
            r = _chaizi.query(ch)
            if r:
                first = r[0]
                if isinstance(first, list):
                    return first
                if isinstance(first, str):
                    return list(first)
        except Exception:
            pass
    return _fallback_components(ch)


def format_radical_info(zh_text):
    if not zh_text:
        return "", ""
    main_list, detail_lines = [], []
    for ch in zh_text:
        if not is_chinese(ch):
            continue
        comps = decompose_char(ch)
        if not comps:
            continue
        main_list.append(radical_label(comps[0]))
        pretty = " + ".join(radical_label(cp) for cp in comps)
        detail_lines.append(f"**{ch}** = {pretty}")
    return ", ".join(main_list), "\n".join(f"• {l}" for l in detail_lines)


POS_MAP = {
    'n': 'Danh từ', 'v': 'Động từ', 'adj': 'Tính từ',
    'adv': 'Trạng từ', 'u': '',
}


def is_chinese(text):
    return any('\u4e00' <= ch <= '\u9fff' for ch in text)


def generate_pinyin(zh_text):
    if not HAS_PINYIN:
        return ""
    try:
        return " ".join([item[0] for item in pinyin(zh_text, style=Style.TONE)])
    except Exception:
        return ""


DB_URL = st.secrets.get("DATABASE_URL", os.environ.get("DATABASE_URL", ""))


class SafeCursor:
    def __init__(self, real_cursor, is_postgres):
        self._cur = real_cursor
        self._is_pg = is_postgres

    def execute(self, sql, params=None):
        if self._is_pg:
            sql = sql.replace('?', '%s')
        if params is not None:
            return self._cur.execute(sql, params)
        return self._cur.execute(sql)

    def fetchall(self):
        return self._cur.fetchall()

    def fetchone(self):
        return self._cur.fetchone()

    def __getattr__(self, name):
        return getattr(self._cur, name)


@st.cache_resource(show_spinner=False)
def _setup_db():
    if DB_URL:
        from sqlalchemy import create_engine
        DB_URL_SAFE = DB_URL.replace("postgresql://", "postgresql+psycopg://")
        _engine = create_engine(DB_URL_SAFE, pool_pre_ping=True,
                                pool_size=2, max_overflow=3, pool_recycle=300)
        _conn = _engine.raw_connection()
        _c = SafeCursor(_conn.cursor(), is_postgres=True)
    else:
        _engine = None
        _conn = sqlite3.connect('vocab_app.db', check_same_thread=False)
        _c = SafeCursor(_conn.cursor(), is_postgres=False)
    return _engine, _conn, _c


@st.cache_resource(show_spinner=False)
def _run_migrations():
    _engine, _conn, _c = _setup_db()
    if DB_URL:
        _c.execute('''CREATE TABLE IF NOT EXISTS flashcards (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            word TEXT, language TEXT, pronunciation TEXT, meaning TEXT,
            example TEXT, level INTEGER DEFAULT 0,
            next_review DATE DEFAULT CURRENT_DATE, pos TEXT, related_words TEXT,
            ease_factor REAL DEFAULT 2.5, interval_days INTEGER DEFAULT 0,
            repetitions INTEGER DEFAULT 0, created_at DATE DEFAULT CURRENT_DATE,
            synonyms TEXT)''')
        _conn.commit()
        for col, ddl in [("pos","TEXT"),("related_words","TEXT"),
            ("ease_factor","REAL DEFAULT 2.5"),("interval_days","INTEGER DEFAULT 0"),
            ("repetitions","INTEGER DEFAULT 0"),("created_at","DATE DEFAULT CURRENT_DATE"),
            ("synonyms","TEXT")]:
            try:
                _c.execute(f"ALTER TABLE flashcards ADD COLUMN IF NOT EXISTS {col} {ddl}")
                _conn.commit()
            except Exception:
                _conn.rollback()
        _c.execute('''CREATE TABLE IF NOT EXISTS study_history (
            study_date TEXT PRIMARY KEY, reviews_count INTEGER DEFAULT 0)''')
        _conn.commit()
    else:
        _c.execute('''CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT, language TEXT, pronunciation TEXT, meaning TEXT,
            example TEXT, level INTEGER DEFAULT 0, next_review DATE,
            pos TEXT, related_words TEXT, ease_factor REAL DEFAULT 2.5,
            interval_days INTEGER DEFAULT 0, repetitions INTEGER DEFAULT 0,
            created_at DATE, synonyms TEXT)''')
        for col, ddl in [("pos","TEXT"),("related_words","TEXT"),
            ("ease_factor","REAL DEFAULT 2.5"),("interval_days","INTEGER DEFAULT 0"),
            ("repetitions","INTEGER DEFAULT 0"),("created_at","DATE"),("synonyms","TEXT")]:
            try:
                _c.execute(f"ALTER TABLE flashcards ADD COLUMN {col} {ddl}")
            except Exception:
                pass
        _c.execute('''CREATE TABLE IF NOT EXISTS study_history (
            study_date TEXT PRIMARY KEY, reviews_count INTEGER DEFAULT 0)''')
        _conn.commit()
    return True


engine, conn, c = _setup_db()
_run_migrations()


@st.cache_data(ttl=120, show_spinner=False)
def get_all_words_cached():
    if engine:
        df = pd.read_sql_query("SELECT * FROM flashcards ORDER BY id DESC", engine)
    else:
        df = pd.read_sql_query("SELECT * FROM flashcards ORDER BY id DESC", conn)
    for col in ['next_review', 'created_at']:
        if col in df.columns:
            df[col] = df[col].astype(str)
    return df


@st.cache_data(ttl=120, show_spinner=False)
def get_stats_cached():
    today_iso = datetime.now().date().isoformat()
    try:
        c.execute("SELECT COUNT(*) FROM flashcards")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM flashcards WHERE next_review <= ?", (today_iso,))
        due = c.fetchone()[0]
        return {'total': total, 'due': due}
    except Exception:
        return {'total': 0, 'due': 0}


@st.cache_data(ttl=120, show_spinner=False)
def get_streak_cached():
    try:
        c.execute("SELECT study_date FROM study_history ORDER BY study_date DESC")
        rows = c.fetchall()
        if not rows:
            return 0, 0
        dates = [datetime.fromisoformat(str(r[0])).date() for r in rows]
        today = datetime.now().date()
        streak = 0
        check_date = today
        date_set = set(dates)
        if today not in date_set:
            check_date = today - timedelta(days=1)
        while check_date in date_set:
            streak += 1
            check_date -= timedelta(days=1)
        c.execute("SELECT reviews_count FROM study_history WHERE study_date = ?",
                  (today.isoformat(),))
        r2 = c.fetchone()
        return streak, (r2[0] if r2 else 0)
    except Exception:
        return 0, 0


def get_all_words():
    return get_all_words_cached()


def invalidate_cache():
    get_all_words_cached.clear()
    get_stats_cached.clear()


# ==========================================
# TRANSLATION
# ==========================================
@st.cache_data(ttl=86400, show_spinner=False)
def _google_translate(text, target='vi'):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target}&dt=t&q={urllib.parse.quote(text)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            result = "".join([item[0] for item in data[0] if item[0]])
            return result if result else None
    except Exception:
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def _mymemory_translate(text, target='vi'):
    try:
        src = 'en' if target == 'vi' else 'vi'
        url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text[:500])}&langpair={src}|{target}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('responseStatus') == 200:
                t = data.get('responseData', {}).get('translatedText', '')
                if t and t.lower().strip() != text.lower().strip():
                    return t
    except Exception:
        pass
    return None


def translate_text(text, target_lang='vi'):
    if not text or not text.strip():
        return None
    result = _google_translate(text, target_lang)
    if result:
        return result
    return _mymemory_translate(text, target_lang)


# ==========================================
# ENGLISH INFO — VERSION 4 (bust cache cũ)
# ==========================================
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_english_v4(word):
    clean = word.strip().lower()
    result = {
        'suggestion': None,
        'ipa': '',
        'pos': '',
        'defs': '',
        'synonyms': [],
    }
    if not clean:
        return result

    # ============ TẦNG 1: eng_to_ipa (offline, 0ms) ============
    if HAS_ENG_IPA:
        try:
            ipa = _ipa_lib.convert(clean)
            if ipa and '*' not in ipa:
                if not ipa.startswith('/'):
                    ipa = '/' + ipa + '/'
                result['ipa'] = ipa
        except Exception:
            pass

    # ============ TẦNG 2: Datamuse ============
    try:
        url = f"https://api.datamuse.com/words?sp={urllib.parse.quote(clean)}&md=pdrs&max=5"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        entry = None
        for e in data:
            if e.get('word', '').lower() == clean:
                entry = e
                break
        if not entry and data:
            entry = data[0]

        if entry:
            if not result['ipa']:
                pron = entry.get('pron')
                if pron:
                    result['ipa'] = arpabet_to_ipa(pron)

            pos_list = []
            for tag in entry.get('tags', []):
                if tag in POS_MAP and POS_MAP[tag] and POS_MAP[tag] not in pos_list:
                    pos_list.append(POS_MAP[tag])
            result['pos'] = ", ".join(pos_list)

            defs_lines = []
            for d in entry.get('defs', [])[:3]:
                if '\t' in d:
                    p_code, definition = d.split('\t', 1)
                    p_vn = POS_MAP.get(p_code.strip(), p_code.strip())
                    prefix = f"[{p_vn}] " if p_vn else ""
                    def_vn = translate_text(definition[:200])
                    if def_vn:
                        defs_lines.append(f"• {prefix}{def_vn}")
                    else:
                        defs_lines.append(f"• {prefix}{definition}")
            result['defs'] = "\n".join(defs_lines)
    except Exception:
        pass

    # ============ TẦNG 3: dictionaryapi.dev (chỉ khi IPA vẫn trống) ============
    if not result['ipa']:
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(clean)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            if isinstance(data, list) and data:
                entry = data[0]
                if entry.get('phonetic'):
                    result['ipa'] = entry['phonetic'].strip('/')
                elif entry.get('phonetics'):
                    for p in entry['phonetics']:
                        if p.get('text'):
                            result['ipa'] = p['text'].strip('/')
                            break
        except Exception:
            pass

    # ============ Synonyms ============
    try:
        url = f"https://api.datamuse.com/words?rel_syn={urllib.parse.quote(clean)}&max=8"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        result['synonyms'] = [e['word'] for e in data if 'word' in e]
    except Exception:
        pass

    # ============ Suggestion ============
    try:
        url = f"https://api.datamuse.com/sug?s={urllib.parse.quote(clean)}&max=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if data and data[0]['word'].lower() != clean:
            result['suggestion'] = data[0]['word']
    except Exception:
        pass

    return result


def make_tts(text, lang):
    if not HAS_TTS:
        return None
    try:
        tts = gTTS(text=text, lang=lang)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        return buf.getvalue()
    except Exception:
        return None


def log_review():
    today = datetime.now().date().isoformat()
    c.execute("SELECT reviews_count FROM study_history WHERE study_date = ?", (today,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE study_history SET reviews_count = ? WHERE study_date = ?",
                  (row[0] + 1, today))
    else:
        c.execute("INSERT INTO study_history (study_date, reviews_count) VALUES (?, ?)",
                  (today, 1))
    conn.commit()
    get_streak_cached.clear()


def get_word_of_day(df):
    if df.empty:
        return None
    today = datetime.now().date().isoformat()
    seed = int(today.replace('-', ''))
    rng = random.Random(seed)
    return df.iloc[rng.randint(0, len(df) - 1)]


def add_word(word, language, pronunciation, meaning, example, pos, related_words, synonyms=""):
    today = datetime.now().date().isoformat()
    c.execute('''INSERT INTO flashcards
                 (word, language, pronunciation, meaning, example, level, next_review,
                  pos, related_words, ease_factor, interval_days, repetitions, created_at, synonyms)
                 VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, 2.5, 0, 0, ?, ?)''',
              (word, language, pronunciation, meaning, example, today,
               pos, related_words, today, synonyms))
    conn.commit()
    invalidate_cache()


def delete_word(word_id):
    c.execute("DELETE FROM flashcards WHERE id = ?", (word_id,))
    conn.commit()
    invalidate_cache()


def get_due_words():
    today = datetime.now().date().isoformat()
    c.execute("SELECT * FROM flashcards WHERE next_review <= ? ORDER BY next_review ASC", (today,))
    return c.fetchall()


def update_review_sm2(word_id, quality, ease, interval, reps):
    if quality < 3:
        reps, interval = 0, 1
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * ease)
        reps += 1
    ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ease = max(1.3, ease)
    next_review = (datetime.now().date() + timedelta(days=interval)).isoformat()
    c.execute("""UPDATE flashcards SET ease_factor=?, interval_days=?, repetitions=?,
                 next_review=?, level=? WHERE id=?""",
              (ease, interval, reps, next_review, reps, word_id))
    conn.commit()
    invalidate_cache()
    log_review()


st.title("📚 Flashcard Pro — Anh & Trung")

if 'show_answer' not in st.session_state:
    st.session_state.show_answer = False

for _k in ['auto_meaning', 'auto_pronun', 'auto_pos', 'auto_related',
           'auto_example', 'auto_synonyms', 'suggestion', 'word_input']:
    if _k not in st.session_state:
        st.session_state[_k] = "" if _k != 'suggestion' else None


def _clear_auto_fields():
    for k in ['auto_meaning', 'auto_pronun', 'auto_pos', 'auto_related',
              'auto_example', 'auto_synonyms']:
        st.session_state[k] = ""
    st.session_state.suggestion = None


with st.sidebar:
    st.markdown("## 🎯 MENU CHÍNH")
    menu = ["➕ Thêm từ mới", "🧠 Ôn tập Flashcard", "🎮 Luyện tập",
            "🗂️ Kho từ vựng", "📊 Thống kê"]
    choice = st.radio("Chọn chức năng", menu, label_visibility="collapsed")

    st.markdown("---")

    streak, today_count = get_streak_cached()
    if streak > 0:
        fire = "🔥" * min(streak, 5)
        st.markdown(
            f"<div class='streak-fire'>{fire}<br>"
            f"<b>{streak} ngày liên tục</b><br>"
            f"<span style='font-size:0.9rem;color:#cbd5e1'>Hôm nay: {today_count} lượt</span>"
            f"</div>", unsafe_allow_html=True
        )
    else:
        st.info("🌱 Bắt đầu học hôm nay để tạo streak!")

    st.markdown("---")

    stats = get_stats_cached()
    c1, c2 = st.columns(2)
    with c1:
        st.metric("📌 Đến hạn", stats['due'])
    with c2:
        st.metric("📚 Tổng", stats['total'])

    st.markdown("---")

    if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
        invalidate_cache()
        get_streak_cached.clear()
        st.rerun()

    st.caption("💡 Mẹo: Ôn tập mỗi ngày để không quên nhé!")


if choice == "➕ Thêm từ mới":
    st.header("✨ Thêm từ vựng mới")

    col1, col2 = st.columns([2, 1])
    with col1:
        language = st.selectbox("Ngôn ngữ", ["Tiếng Anh", "Tiếng Trung"])
        word_label = "Từ vựng / Pinyin" if language == "Tiếng Trung" else "Từ vựng (Tiếng Anh)"
        word = st.text_input(
            word_label,
            key="word_input",
            on_change=_clear_auto_fields,
            placeholder="Ví dụ: 你好 hoặc ni hao" if language == "Tiếng Trung" else "Ví dụ: wonderful"
        )

    with col2:
        st.write("##")
        if st.button("⚡ Dịch siêu nhanh", use_container_width=True):
            if word and word.strip():
                _clear_auto_fields()
                with st.spinner("🔮 Đang phân tích..."):
                    if language == "Tiếng Anh":
                        info = fetch_english_v4(word)
                        meaning_vn = translate_text(word, 'vi')
                        st.session_state.auto_meaning = meaning_vn or ""
                        st.session_state.auto_pronun = info['ipa']
                        st.session_state.auto_pos = info['pos']
                        st.session_state.auto_related = info['defs']
                        st.session_state.auto_synonyms = ", ".join(info['synonyms'])
                        st.session_state.suggestion = info['suggestion']
                    else:
                        meaning_vn = translate_text(word, 'vi')
                        st.session_state.auto_meaning = meaning_vn or ""
                        st.session_state.suggestion = None
                        st.session_state.auto_synonyms = ""
                        if is_chinese(word):
                            st.session_state.auto_pronun = generate_pinyin(word)
                            main_rad, detail = format_radical_info(word)
                            st.session_state.auto_pos = main_rad or "Chữ Hán"
                            st.session_state.auto_related = detail
                        else:
                            st.session_state.auto_pronun = word
                            st.session_state.auto_pos = "Nhập bằng Pinyin"
                            st.session_state.auto_related = ""
                st.toast("✨ Đã phân tích xong!", icon="✅")
            else:
                st.warning("Hãy nhập từ trước.")

    sug_word = st.session_state.get('suggestion', None)
    if sug_word and language == "Tiếng Anh":
        st.warning(f"💡 Có phải bạn muốn gõ: **{sug_word}**?")
        if st.button(f"👉 Sửa thành '{sug_word}' và dịch lại"):
            st.session_state.word_input = sug_word
            _clear_auto_fields()
            st.rerun()

    meaning_default = st.session_state.get('auto_meaning', "")
    pronun_default = st.session_state.get('auto_pronun', "")
    pos_default = st.session_state.get('auto_pos', "")
    related_default = st.session_state.get('auto_related', "")
    synonyms_default = st.session_state.get('auto_synonyms', "")

    pos_label = "Bộ thủ / Loại từ" if language == "Tiếng Trung" else "Loại từ"
    related_label = "Cấu tạo chữ Hán" if language == "Tiếng Trung" else "Định nghĩa chi tiết (đã dịch)"

    col_a, col_b = st.columns(2)
    with col_a:
        pronunciation = st.text_input("Phiên âm (IPA / Pinyin)", value=pronun_default)
    with col_b:
        pos = st.text_input(pos_label, value=pos_default)

    meaning = st.text_input("Nghĩa tiếng Việt", value=meaning_default)
    related_words = st.text_area(related_label, value=related_default, height=100)

    if language == "Tiếng Anh":
        synonyms = st.text_input("Từ đồng nghĩa", value=synonyms_default)
    else:
        synonyms = ""

    example = st.text_area("Câu ví dụ (không bắt buộc)", height=80)

    if word and HAS_TTS:
        tts_lang = 'en' if language == "Tiếng Anh" else 'zh-CN'
        if st.button("🔊 Nghe thử phát âm"):
            audio_bytes = make_tts(word, tts_lang)
            if audio_bytes:
                st.audio(audio_bytes, format='audio/mp3')

    if st.button("💾 Lưu từ vựng", use_container_width=True, type="primary"):
        if word and meaning:
            add_word(word, language, pronunciation, meaning, example, pos, related_words, synonyms)
            st.toast(f"💾 Đã lưu: {word}", icon="✅")
            _clear_auto_fields()
            st.session_state.word_input = ""
            st.rerun()
        else:
            st.error("Vui lòng điền Từ vựng và Nghĩa!")

    st.markdown("---")

    with st.expander("📥 Nhập hàng loạt từ file CSV"):
        st.markdown("Cột theo thứ tự: `word, language, pronunciation, meaning, example, pos`")
        st.code("word,language,pronunciation,meaning,example,pos\nhello,Tiếng Anh,həˈloʊ,xin chào,Hello world!,Thán từ", language="csv")

        uploaded = st.file_uploader("Chọn file CSV", type=['csv'])
        if uploaded is not None:
            try:
                df_imp = pd.read_csv(uploaded)
                st.success(f"✅ Đọc được {len(df_imp)} dòng")
                st.dataframe(df_imp.head(10))

                if st.button("🚀 Import tất cả", type="primary"):
                    count = 0
                    for _, r in df_imp.iterrows():
                        try:
                            add_word(
                                str(r.get('word', '')).strip(),
                                str(r.get('language', 'Tiếng Anh')).strip(),
                                str(r.get('pronunciation', '')).strip() if pd.notna(r.get('pronunciation')) else "",
                                str(r.get('meaning', '')).strip(),
                                str(r.get('example', '')).strip() if pd.notna(r.get('example')) else "",
                                str(r.get('pos', '')).strip() if pd.notna(r.get('pos')) else "",
                                "",
                                str(r.get('synonyms', '')).strip() if pd.notna(r.get('synonyms')) else ""
                            )
                            count += 1
                        except Exception:
                            pass
                    st.toast(f"🎉 Đã import {count} từ!", icon="✅")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Lỗi: {e}")

        template = "word,language,pronunciation,meaning,example,pos\nhello,Tiếng Anh,həˈloʊ,xin chào,Hello world!,Thán từ\n"
        st.download_button("📄 Tải file mẫu CSV", data=template,
                          file_name="flashcard_template.csv", mime="text/csv")


elif choice == "🧠 Ôn tập Flashcard":
    st.header("🧠 Ôn tập hàng ngày")

    df_all = get_all_words()
    wotd = get_word_of_day(df_all)
    if wotd is not None:
        st.markdown(f"""
        <div class='wotd-card'>
            <div style='font-size:0.9rem; color:#a78bfa; margin-bottom:5px'>✨ WORD OF THE DAY ✨</div>
            <div class='wotd-word'>{wotd['word']}</div>
            <div style='color:#94a3b8; font-size:1rem'>{wotd['meaning']}</div>
        </div>
        """, unsafe_allow_html=True)

    due_words = get_due_words()
    total_due = len(due_words)

    if total_due > 0:
        today_iso = datetime.now().date().isoformat()
        total_all = len(df_all[df_all['next_review'] <= today_iso]) if not df_all.empty else total_due
        done = max(0, total_all - total_due)
        progress = done / total_all if total_all > 0 else 0

        st.progress(progress, text=f"📊 Tiến độ: {done}/{total_all} từ")
        st.info(f"Còn **{total_due}** từ cần ôn!")

        card = due_words[0]
        word_id, word, lang, pron, meaning, example, level = card[0:7]
        pos = card[8] if len(card) > 8 and card[8] else ""
        related = card[9] if len(card) > 9 and card[9] else ""
        ease = card[10] if len(card) > 10 and card[10] is not None else 2.5
        interval = card[11] if len(card) > 11 and card[11] is not None else 0
        reps = card[12] if len(card) > 12 and card[12] is not None else 0
        synonyms_val = card[14] if len(card) > 14 and card[14] else ""

        st.markdown(f"<div class='flashcard-word'>{word}</div>", unsafe_allow_html=True)
        sub_info = []
        if pron:
            sub_info.append(f"/{pron}/")
        if pos:
            sub_info.append(f"[{pos}]")
        if sub_info:
            st.markdown(f"<h4 style='text-align:center; color:#94a3b8;'>{' • '.join(sub_info)}</h4>",
                        unsafe_allow_html=True)

        if HAS_TTS:
            tts_lang = 'en' if lang == "Tiếng Anh" else 'zh-CN'
            c1, c2, c3 = st.columns([1, 1, 1])
            with c2:
                if st.button("🔊 Nghe phát âm", use_container_width=True):
                    audio_bytes = make_tts(word, tts_lang)
                    if audio_bytes:
                        st.audio(audio_bytes, format='audio/mp3')

        st.write("---")

        if not st.session_state.show_answer:
            if st.button("👁️ Xem đáp án", use_container_width=True):
                st.session_state.show_answer = True
                st.rerun()

        if st.session_state.show_answer:
            st.success(f"**Nghĩa:** {meaning}")
            if synonyms_val:
                st.markdown(f"**Từ đồng nghĩa:** {synonyms_val}")
            if related:
                st.markdown(f"**Định nghĩa chi tiết:**\n\n{related}")
            if example:
                st.info(f"**Ví dụ:** {example}")
            st.write("---")
            st.caption(f"📈 Lần ôn: **{reps}** • Interval: **{interval}** ngày • Ease: **{ease:.2f}**")
            st.write("Đánh giá mức độ nhớ:")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("❌ Quên", use_container_width=True):
                    update_review_sm2(word_id, 0, ease, interval, reps)
                    st.session_state.show_answer = False
                    st.rerun()
            with col2:
                if st.button("😰 Khó", use_container_width=True):
                    update_review_sm2(word_id, 3, ease, interval, reps)
                    st.session_state.show_answer = False
                    st.rerun()
            with col3:
                if st.button("🙂 Tốt", use_container_width=True):
                    update_review_sm2(word_id, 4, ease, interval, reps)
                    st.session_state.show_answer = False
                    st.rerun()
            with col4:
                if st.button("😎 Dễ", use_container_width=True):
                    update_review_sm2(word_id, 5, ease, interval, reps)
                    st.session_state.show_answer = False
                    st.rerun()
    else:
        st.balloons()
        st.success("Tuyệt vời! Bạn đã hoàn thành toàn bộ bài học hôm nay. 🎉")


elif choice == "🎮 Luyện tập":
    st.header("🎮 Luyện tập")
    df = get_all_words()

    if len(df) < 4:
        st.warning("⚠️ Cần ít nhất **4 từ** để luyện tập!")
        st.stop()

    for key in ['practice_q', 'practice_answered', 'practice_score', 'practice_total', 'practice_feedback']:
        if key not in st.session_state:
            st.session_state[key] = None if key in ('practice_q', 'practice_feedback') else (
                False if key == 'practice_answered' else 0)

    c1, c2 = st.columns(2)
    with c1:
        st.metric("✅ Đúng", st.session_state.practice_score)
    with c2:
        st.metric("📊 Tổng câu", st.session_state.practice_total)

    mode = st.radio("Chế độ:",
        ["⌨️ Gõ từ", "🎯 Trắc nghiệm", "🎧 Nghe & gõ"],
        horizontal=True, label_visibility="collapsed")

    st.write("---")

    if st.session_state.practice_q is None and not st.session_state.practice_answered:
        st.session_state.practice_q = df.sample(1).iloc[0].to_dict()
        st.session_state.practice_total += 1

    q = st.session_state.practice_q
    if not q:
        st.stop()

    q_word = q['word']
    q_meaning = q['meaning']
    q_lang = q['language']
    q_pron = q.get('pronunciation') or ""
    tts_lang = 'en' if q_lang == "Tiếng Anh" else 'zh-CN'

    if mode == "⌨️ Gõ từ":
        st.caption("📝 Nhìn nghĩa → gõ lại từ")
        st.markdown(f"<div class='practice-word'>{q_meaning}</div>", unsafe_allow_html=True)
        if q_pron:
            st.caption(f"Gợi ý phiên âm: /{q_pron}/")

        user_ans = st.text_input("Gõ từ:", key="typing_input",
            disabled=st.session_state.practice_answered)

        col1, col2 = st.columns(2)
        with col1:
            if not st.session_state.practice_answered:
                if st.button("✅ Kiểm tra", use_container_width=True, type="primary"):
                    if user_ans.strip().lower() == q_word.strip().lower():
                        st.session_state.practice_feedback = "correct"
                        st.session_state.practice_score += 1
                    else:
                        st.session_state.practice_feedback = "wrong"
                    st.session_state.practice_answered = True
                    st.rerun()
        with col2:
            if st.session_state.practice_answered:
                if st.button("➡️ Câu tiếp", use_container_width=True):
                    st.session_state.practice_q = None
                    st.session_state.practice_answered = False
                    st.session_state.practice_feedback = None
                    st.rerun()

        if st.session_state.practice_answered:
            if st.session_state.practice_feedback == "correct":
                st.success(f"🎉 Chính xác! Đáp án: **{q_word}**")
            else:
                st.error(f"❌ Sai rồi. Đáp án: **{q_word}**")

    elif mode == "🎯 Trắc nghiệm":
        st.caption("🎯 Nhìn từ → chọn nghĩa đúng")
        st.markdown(f"<div class='practice-word'>{q_word}</div>", unsafe_allow_html=True)
        if q_pron:
            st.caption(f"/{q_pron}/")

        wrong_pool = df[df['id'] != q['id']]['meaning'].dropna().unique().tolist()
        wrongs = random.sample(wrong_pool, min(3, len(wrong_pool)))
        options = [q_meaning] + wrongs
        random.shuffle(options)

        if not st.session_state.practice_answered:
            for i, opt in enumerate(options):
                if st.button(f"{chr(65+i)}. {opt}", key=f"quiz_{i}", use_container_width=True):
                    if opt == q_meaning:
                        st.session_state.practice_feedback = "correct"
                        st.session_state.practice_score += 1
                    else:
                        st.session_state.practice_feedback = "wrong"
                    st.session_state.practice_answered = True
                    st.rerun()
        else:
            for i, opt in enumerate(options):
                prefix = "✅" if opt == q_meaning else "❌"
                st.markdown(f"{prefix} **{chr(65+i)}. {opt}**")
            if st.session_state.practice_feedback == "correct":
                st.success("🎉 Đúng rồi!")
            else:
                st.error(f"❌ Sai. Đáp án: **{q_meaning}**")
            if st.button("➡️ Câu tiếp", use_container_width=True):
                st.session_state.practice_q = None
                st.session_state.practice_answered = False
                st.session_state.practice_feedback = None
                st.rerun()

    elif mode == "🎧 Nghe & gõ":
        st.caption("🎧 Nghe phát âm → gõ lại từ")
        if HAS_TTS:
            audio_bytes = make_tts(q_word, tts_lang)
            if audio_bytes:
                st.audio(audio_bytes, format='audio/mp3')
        st.caption(f"Gợi ý nghĩa: {q_meaning}")

        user_ans = st.text_input("Gõ từ bạn nghe được:", key="shadow_input",
            disabled=st.session_state.practice_answered)

        col1, col2 = st.columns(2)
        with col1:
            if not st.session_state.practice_answered:
                if st.button("✅ Kiểm tra", use_container_width=True, type="primary"):
                    if user_ans.strip().lower() == q_word.strip().lower():
                        st.session_state.practice_feedback = "correct"
                        st.session_state.practice_score += 1
                    else:
                        st.session_state.practice_feedback = "wrong"
                    st.session_state.practice_answered = True
                    st.rerun()
        with col2:
            if st.session_state.practice_answered:
                if st.button("➡️ Câu tiếp", use_container_width=True):
                    st.session_state.practice_q = None
                    st.session_state.practice_answered = False
                    st.session_state.practice_feedback = None
                    st.rerun()

        if st.session_state.practice_answered:
            if st.session_state.practice_feedback == "correct":
                st.success(f"🎉 Chính xác! Đáp án: **{q_word}**")
            else:
                st.error(f"❌ Sai. Đáp án: **{q_word}**")

    st.write("---")
    if st.button("🔄 Reset điểm"):
        st.session_state.practice_score = 0
        st.session_state.practice_total = 0
        st.session_state.practice_q = None
        st.session_state.practice_answered = False
        st.session_state.practice_feedback = None
        st.rerun()


elif choice == "🗂️ Kho từ vựng":
    st.header("🗂️ Kho từ vựng")
    df = get_all_words()

    if df.empty:
        st.info("Kho từ vựng đang trống.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            search = st.text_input("🔍 Tìm từ / nghĩa", "")
        with col2:
            lang_filter = st.selectbox("Ngôn ngữ", ["Tất cả", "Tiếng Anh", "Tiếng Trung"])
        with col3:
            level_filter = st.selectbox("Cấp độ", ["Tất cả"] + [str(i) for i in range(0, 8)])

        filtered = df.copy()
        if search:
            mask = (filtered['word'].str.contains(search, case=False, na=False)) | \
                   (filtered['meaning'].str.contains(search, case=False, na=False))
            filtered = filtered[mask]
        if lang_filter != "Tất cả":
            filtered = filtered[filtered['language'] == lang_filter]
        if level_filter != "Tất cả":
            filtered = filtered[filtered['level'] == int(level_filter)]

        st.caption(f"Hiển thị **{len(filtered)}** / {len(df)} từ")

        for _, row in filtered.iterrows():
            pos_tag = f" [{row['pos']}]" if pd.notna(row.get('pos')) and row['pos'] else ""
            with st.expander(f"📌 **{row['word']}**{pos_tag} ({row['language']}) — {row['meaning']}"):
                st.write(f"- **Phiên âm:** {row['pronunciation']}")
                if pd.notna(row.get('pos')) and row['pos']:
                    st.write(f"- **Loại từ / Bộ thủ:** {row['pos']}")
                if pd.notna(row.get('synonyms')) and row['synonyms']:
                    st.write(f"- **Từ đồng nghĩa:** {row['synonyms']}")
                if pd.notna(row.get('related_words')) and row['related_words']:
                    st.markdown(f"- **Định nghĩa:**\n\n{row['related_words']}")
                if pd.notna(row.get('example')) and row['example']:
                    st.write(f"- **Ví dụ:** {row['example']}")
                st.write(f"- **Lần ôn:** {row.get('repetitions', 0)} | **Ôn tiếp:** {row['next_review']}")

                btn_col1, btn_col2 = st.columns([1, 4])
                with btn_col1:
                    if st.button("🗑️ Xóa", key=f"del_{row['id']}"):
                        delete_word(row['id'])
                        st.toast("🗑️ Đã xóa!", icon="✅")
                        st.rerun()
                with btn_col2:
                    if HAS_TTS:
                        tts_lang = 'en' if row['language'] == "Tiếng Anh" else 'zh-CN'
                        if st.button("🔊 Nghe", key=f"tts_{row['id']}"):
                            audio_bytes = make_tts(row['word'], tts_lang)
                            if audio_bytes:
                                st.audio(audio_bytes, format='audio/mp3')


elif choice == "📊 Thống kê":
    st.header("📊 Thống kê")
    df = get_all_words()

    if df.empty:
        st.info("Chưa có dữ liệu.")
    else:
        today = datetime.now().date()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📚 Tổng", len(df))
        with col2:
            due = len(df[df['next_review'] <= today.isoformat()])
            st.metric("⏰ Đến hạn", due)
        with col3:
            week_ago = (today - timedelta(days=7)).isoformat()
            new_week = len(df[df['created_at'] >= week_ago]) if 'created_at' in df else 0
            st.metric("🆕 Tuần này", new_week)
        with col4:
            mastered = len(df[df['level'] >= 5])
            st.metric("🏆 Đã thuộc", mastered)

        st.markdown("---")
        streak, today_count = get_streak_cached()
        c1, c2 = st.columns(2)
        with c1:
            st.metric("🔥 Streak", f"{streak} ngày")
        with c2:
            st.metric("📖 Ôn hôm nay", f"{today_count} lượt")

        st.markdown("---")
        st.subheader("📈 Phân bố theo cấp độ")
        st.bar_chart(df['level'].value_counts().sort_index())

        st.markdown("---")
        st.subheader("🌐 Theo ngôn ngữ")
        st.bar_chart(df['language'].value_counts())

        st.markdown("---")
        st.subheader("📅 Từ mới 7 ngày gần nhất")
        if 'created_at' in df:
            recent = df[df['created_at'] >= (today - timedelta(days=7)).isoformat()]
            if not recent.empty:
                st.bar_chart(recent.groupby('created_at').size())

        st.markdown("---")
        st.subheader("⬇️ Xuất dữ liệu")
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Tải CSV", data=csv_data,
            file_name=f"flashcards_{today.isoformat()}.csv", mime="text/csv")
