# meteoAgent

Automazioni Python per scraping meteo e notifiche Telegram.

## 🌤️ Scraper Universale iLMeteo (`ilmeteo_scraper.py`)

`ilmeteo_scraper.py` legge i 7 giorni disponibili da iLMeteo.it per **qualsiasi comune** (es. Cusago, Gioiosa Marea, Milano, ecc.), estrae i dati orari e formatta un report Telegram con **badge cromatici per facilitare la lettura visiva del rischio**.

### 🌟 Funzionalità principale

- **Multi-comune**: supporta qualsiasi località specificabile da riga di comando o via `.env`.
- **Riconoscimento automatico del Mare**:
  - Per comuni di mare (es. Gioiosa Marea) estrae l'altezza delle onde e mostra il badge del mare (`🟢`, `🟠`, `🔴`).
  - Per comuni d'entroterra (es. Cusago) omette automaticamente la colonna delle onde.
- **Riconoscimento fenomeno e livello di pioggia**:
  - `☀️ Precipitazioni: Assenti` (giornate di sole)
  - `🟡 ☔ Pioggia debole` ($\le 2\text{ mm}$)
  - `🟠 🌧️ Pioggia moderata` ($2 - 5\text{ mm}$)
  - `🔴 ⛈️ Pioggia forte` ($> 5\text{ mm}$)
  - `❄️ Neve` e `🌫️ Nebbia`
- **Rischio Grandine**: mostra il picco di probabilità grandine solo se $> 0\%$ (`🟡`, `🟠`, `🔴`).
- **Range Temperature**: badge visivo per freddo, mite, caldo e canicola (`🔵`, `🟢`, `🟠`, `🔴`).

---

### 💻 Esecuzione da terminale

```bash
# Esecuzione per Cusago
python ilmeteo_scraper.py cusago

# Esecuzione per Gioiosa Marea
python ilmeteo_scraper.py gioiosa marea
```

---

### ⚙️ Configurazione Telegram (`.env`)

Crea o modifica il file `.env`:

```env
TELEGRAM_BOT_TOKEN=8948798566:AAFN7uQMCM3azYx58CiAl5W7vGINaPbVnGk
TELEGRAM_RECEIVER_ID=5872825403
```

---

### ⏰ Configurazione Cron su Raspberry Pi

Modifica `run_meteo.sh` ed eseguilo nel crontab:

```cron
0 8,20 * * * cd $HOME/meteoAgent && ./run_meteo.sh >> $HOME/meteoAgent/meteo.log 2>&1
```
