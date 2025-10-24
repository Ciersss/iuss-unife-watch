# 🕵️‍♂️ IUSS UNIFE Watch

Un piccolo **scraper** per controllare automaticamente il sito di **UniFe** (Università di Ferrara) e ricevere **notifiche su Telegram** quando ci sono modifiche su una pagina configurata.  
Lo scopo principale è ricevere un avviso quando vengono pubblicati **nuovi risultati dei bandi** o aggiornamenti simili.

> ⚠️ Progetto nato in 5 minuti di ispirazione, quindi aspettati qualche stranezza o logica discutibile che nella mia testa aveva perfettamente senso all’epoca

---

## 🚀 Funzionalità

- Monitora una o più pagine del sito UniFe (o altre pagine configurabili)
- Invia notifiche via **Telegram Bot API**
- Salva lo stato precedente per capire se la pagina è cambiata
- Leggero, senza dipendenze pesanti
- Facile da lanciare con **Docker** o da terminale

---

## 🧰 Requisiti

- **Python 3.10+**
- Un **bot Telegram** (creato con [@BotFather](https://t.me/BotFather))
- Una **chat ID** dove inviare le notifiche

---

## ⚙️ Installazione

### 1️⃣ Clona il repository
```bash
git clone https://github.com/tuonome/iuss-unife-watch.git
cd iuss-unife-watch
```

### 2️⃣ Crea l’ambiente virtuale
```bash
python -m venv .venv
source .venv/bin/activate  # su Linux/macOS
# oppure
.venv\Scripts\activate  # su Windows
```

### 3️⃣ Installa le dipendenze
```bash
pip install -r requirements.txt
```

---

## 🧩 Configurazione

Crea un file `.env` (puoi partire da `.env.example`) e compila i valori necessari:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
WATCH_URL=https://www.unife.it/studenti/concorsi-bandi
CHECK_INTERVAL=300  # secondi tra un controllo e l'altro
```

---

## ▶️ Utilizzo

Per avviare lo scraper:

```bash
python watch_bando_unife.py
```

Oppure, se vuoi usare **Docker**:

```bash
docker-compose up --build
```

Il programma controllerà periodicamente la pagina configurata e, in caso di modifiche, ti invierà un messaggio su Telegram.

---

## 💾 File generati

- `state.json` → memorizza l’hash o lo stato precedente della pagina per confronti futuri  
- `versions/` → (facoltativo) contiene eventuali snapshot o versioni salvate  

---

## 🐛 Note & Avvertenze

- Non è un progetto “di produzione”: è stato fatto velocemente, principalmente per uso personale.  
- Potrebbero esserci errori o scelte logiche “creative”.  
- Se UniFe cambia struttura HTML, lo scraper potrebbe smettere di funzionare.  
- Nessuna garanzia, solo amore, ADHD e caffeina ☕

---

## 🤝 Contributi

Se vuoi sistemare, migliorare o rifattorizzare il disastro — **PR benvenute!**

---

## 📄 Licenza

MIT License — puoi farne ciò che vuoi, ma per favore **non incolparmi se esplode** 🔥

---

## 💬 Autore

Progetto creato da Veaceslav Maftei [Ciersss]  
> “Funzionava sul mio computer.”™
