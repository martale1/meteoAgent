# meteoAgent

Scraper Python per le previsioni meteo e marine di Gioiosa Marea da iLMeteo.it.

Il progetto legge i 7 giorni disponibili nella pagina principale, apre le pagine giornaliere, raccoglie i dati orari e invia un riepilogo formattato su Telegram.

## Funzionalita

- Estrazione temperature minime e massime giornaliere.
- Estrazione ora per ora di onde, vento, raffiche, direzione vento, umidita e pressione.
- Riepilogo giornaliero con range onde e vento.
- Badge onde nel messaggio Telegram:
  - verde sotto 30 cm
  - arancione fino a 50 cm
  - rosso sopra 50 cm
- Link finale alla pagina iLMeteo.

## File generati

Lo script crea questi CSV locali:

- `gioiosa_marea_ilmeteo.csv`: riepilogo per giorno.
- `gioiosa_marea_orario_ilmeteo.csv`: dettaglio orario.

I CSV sono ignorati da Git per evitare di salvare output temporanei nel repository.

## Configurazione Telegram

Copia `.env.example` in `.env`:

```powershell
Copy-Item .env.example .env
```

Poi inserisci i valori reali:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_RECEIVER_ID=your_telegram_chat_id
```

Il file `.env` contiene dati sensibili ed e escluso dal repository tramite `.gitignore`.

## Installazione

Con l'ambiente Conda `openaiAgent`:

```powershell
& "C:\Users\theoi\anaconda3\Scripts\conda.exe" run -n openaiAgent pip install -r requirements.txt
```

## Esecuzione

```powershell
& "C:\Users\theoi\anaconda3\Scripts\conda.exe" run -n openaiAgent python ilmeteo_gioiosa.py
```

Healthcheck sensori AnyIOT:

```powershell
& "C:\Users\theoi\anaconda3\Scripts\conda.exe" run -n openaiAgent python anyiot_healthcheck.py
```

Su Raspberry/Linux puoi usare lo script:

```bash
chmod +x run_meteo.sh
./run_meteo.sh
```

Per l'healthcheck AnyIOT:

```bash
chmod +x run_anyiot_healthcheck.sh
./run_anyiot_healthcheck.sh
```

## Script principali

- `ilmeteo_gioiosa.py`: scraper principale e invio Telegram.
- `anyiot_healthcheck.py`: controllo heartbeat sensori temperatura/umidita AnyIOT.
- `run_meteo.sh`: launcher per Raspberry/Linux con virtualenv automatico.
- `run_anyiot_healthcheck.sh`: launcher per healthcheck AnyIOT.
- `inspect_available_days.py`: verifica i giorni disponibili.
- `inspect_day_ilmeteo.py`: ispezione della tabella meteo giornaliera.
- `inspect_ilmeteo.py`: ispezione della pagina meteo principale.
- `inspect_mare_ilmeteo.py`: ispezione della pagina mare.

## Note

Il sito iLMeteo puo cambiare struttura HTML nel tempo. Se lo scraping smette di funzionare, gli script `inspect_*` aiutano a verificare rapidamente selettori e tabelle disponibili.

## Cron Healthcheck

Per controllare AnyIOT ogni 30 minuti:

```cron
*/30 * * * * cd $HOME/meteoAgent && ./run_anyiot_healthcheck.sh >> $HOME/meteoAgent/anyiot_healthcheck.log 2>&1
```

Di default Telegram viene avvisato solo in caso di problemi:

- pagina non raggiungibile
- nessun sensore estratto
- uno o piu sensori non aggiornati da oltre 45 minuti
