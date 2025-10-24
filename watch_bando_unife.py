import os
import sys
import json
import time
import logging
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

load_dotenv()


# --------- CONFIG ---------
URL = os.getenv("URL")
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", 120))  # default 120
KEEP_VERSIONS = int(os.getenv("KEEP_VERSIONS", 5))  # default 5

# Percorsi
BASE_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent / "iuss_unife_watch"))
STATE_FILE = BASE_DIR / "state.json"
VERSIONS_DIR = BASE_DIR / "versions"
VERSIONS_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (compatible; IUSS-Unife-Watcher/Telegram-Only/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
}


# --------- UTIL ---------
def load_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        logging.warning("Stato corrotto: riparto da zero.")
    return {}

def save_state(state: dict) -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

def sha256(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def fetch_page(url: str, etag: Optional[str], last_modified: Optional[str]) -> Tuple[int, str, Optional[str], Optional[str]]:
    headers = dict(HEADERS_BASE)
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    # piccoli retry
    backoffs = [0, 2, 4]
    for attempt, back in enumerate(backoffs, start=1):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            status = resp.status_code
            if status == 304:
                return status, "", resp.headers.get("ETag"), resp.headers.get("Last-Modified")
            if 200 <= status < 300:
                return status, resp.text, resp.headers.get("ETag"), resp.headers.get("Last-Modified")
            logging.warning("HTTP %s (tentativo %d)", status, attempt)
        except requests.RequestException as e:
            logging.warning("Errore rete %s (tentativo %d)", e, attempt)
        time.sleep(back)
    raise RuntimeError("Impossibile scaricare la pagina dopo vari tentativi.")

def extract_main_text(html: str) -> Tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    candidates = [
        "div#content-core",
        "main",
        "article",
        "div#content",
        "div.portal-column-content",
        "div.section",
    ]
    main = None
    for sel in candidates:
        m = soup.select_one(sel)
        if m and m.get_text(strip=True):
            main = m
            break
    if not main:
        main = soup.body or soup

    cleaned_html = str(main)
    text = main.get_text("\n", strip=True)
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return text, cleaned_html

def send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logging.error("Telegram non configurato: imposta TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID.")
        return

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": False,
        "parse_mode": "HTML",
    }

    # retry leggero
    for attempt in range(3):
        try:
            r = requests.post(api_url, json=payload, timeout=20)
            ok = r.status_code == 200 and r.json().get("ok")
            if ok:
                logging.info("Notifica Telegram inviata.")
                return
            logging.warning("Telegram HTTP %s: %s", r.status_code, r.text[:300])
        except requests.RequestException as e:
            logging.warning("Errore Telegram: %s", e)
        time.sleep(1 + attempt)
    logging.error("Notifica Telegram fallita dopo vari tentativi.")

def list_version_dirs() -> List[Path]:
    if not VERSIONS_DIR.exists():
        return []
    dirs = [d for d in VERSIONS_DIR.iterdir() if d.is_dir()]
    # ordina per nome (timestamp) discendente -> più recenti prima
    return sorted(dirs, key=lambda d: d.name, reverse=True)

def prune_versions(keep: int = KEEP_VERSIONS) -> None:
    dirs = list_version_dirs()
    for old in dirs[keep:]:
        try:
            # rimuovi intera cartella versione
            for p in old.glob("**/*"):
                if p.is_file():
                    p.unlink(missing_ok=True)
            # prova a rimuovere eventuali sotto-directory vuote
            for p in sorted(old.glob("**/*"), reverse=True):
                if p.is_dir():
                    p.rmdir()
            old.rmdir()
            logging.info("Rimossa versione vecchia: %s", old.name)
        except Exception as e:
            logging.warning("Impossibile rimuovere %s: %s", old, e)

def save_version(text: str, html: str) -> Path:
    ver_dir = VERSIONS_DIR / now_ts()
    ver_dir.mkdir(parents=True, exist_ok=True)
    (ver_dir / "content.txt").write_text(text, encoding="utf-8")
    (ver_dir / "content.html").write_text(html, encoding="utf-8")
    return ver_dir


# --------- CONTROLLO UNA VOLTA ---------
def check_once():
    state = load_state()
    etag = state.get("etag")
    last_mod = state.get("last_modified")
    prev_hash = state.get("hash")

    status, html, new_etag, new_last_mod = fetch_page(URL, etag, last_mod)

    if status == 304:
        logging.info("Nessuna modifica (304 Not Modified).")
        return False  # no change

    text, cleaned_html = extract_main_text(html)
    curr_hash = sha256(text)

    if prev_hash and curr_hash == prev_hash:
        logging.info("Nessuna modifica nel contenuto principale.")
        # aggiorna metadati e timestamp di controllo
        state.update({
            "etag": new_etag,
            "last_modified": new_last_mod,
            "last_checked_ts": int(time.time()),
        })
        save_state(state)
        return False  # no change

    # Nuovo contenuto o modifica
    ver_dir = save_version(text, cleaned_html)
    prune_versions(KEEP_VERSIONS)

    state.update({
        "hash": curr_hash,
        "etag": new_etag,
        "last_modified": new_last_mod,
        "last_checked_ts": int(time.time()),
        "url": URL,
        "last_version_dir": str(ver_dir),
    })
    save_state(state)

    # Notifica
    if prev_hash:
        title = "🔔 <b>IUSS Unife – Modifica al Bando 41</b>"
        change_line = "È stata rilevata una <b>modifica</b> al contenuto principale."
    else:
        title = "✅ <b>IUSS Unife – Monitor attivo</b>"
        change_line = "Prima acquisizione del contenuto: verranno segnalate le modifiche."

    msg = (
        f"{title}\n"
        f"{change_line}\n\n"
        f"🔗 <a href=\"{URL}\">Pagina ufficiale</a>\n"
        f"🗂️ Versione salvata: <code>{Path(ver_dir).name}</code>\n"
        f"ℹ️ Copie: {ver_dir}/content.txt e content.html\n"
    )
    send_telegram(msg)
    return True  # changed


# --------- LOOP CONTINUO OGNI 2 MINUTI ---------
def main_loop():
    logging.info("Avvio watcher. Intervallo: %s secondi. URL: %s", CHECK_INTERVAL_SECONDS, URL)
    # controllo immediato all'avvio
    try:
        check_once()
    except Exception as e:
        logging.exception("Errore al primo controllo: %s", e)

    while True:
        try:
            time.sleep(CHECK_INTERVAL_SECONDS)
            check_once()
        except KeyboardInterrupt:
            logging.info("Interrotto dall'utente. Esco.")
            break
        except Exception as e:
            # non fermare il loop; attendo un po' e riprovo
            logging.exception("Errore nel loop: %s", e)
            time.sleep(10)

if __name__ == "__main__":
    main_loop()
