# meteoAgent

Automazioni Python per scraping e notifiche Telegram.

Il repository contiene due scraper separati:

- `ilmeteo_gioiosa.py`: previsioni meteo/mare per Gioiosa Marea da iLMeteo.it.
- `anyiot_healthcheck.py`: controllo heartbeat dei sensori temperatura/umidita AnyIOT.

I due script sono indipendenti: puoi eseguirli e schedularli separatamente.

## Scraper 1: Meteo Gioiosa Marea

`ilmeteo_gioiosa.py` legge i 7 giorni disponibili da iLMeteo.it, apre le pagine giornaliere e raccoglie i dati orari.

Funzionalita:

- temperature minime e massime giornaliere
- onde, vento, raffiche e direzione vento ora per ora
- umidita e pressione
- riepilogo Telegram formattato
- badge onde nel messaggio Telegram:
  - verde sotto 30 cm
  - arancione fino a 50 cm
  - rosso sopra 50 cm
- link finale alla pagina iLMeteo

File generati:

- `gioiosa_marea_ilmeteo.csv`: riepilogo giornaliero
- `gioiosa_marea_orario_ilmeteo.csv`: dettaglio orario

Esecuzione:

```bash
./run_meteo.sh
```

Oppure direttamente:

```bash
python ilmeteo_gioiosa.py
```

Cron suggerito, ogni giorno alle 8:00 e alle 20:00:

```cron
0 8,20 * * * cd $HOME/meteoAgent && ./run_meteo.sh >> $HOME/meteoAgent/meteo.log 2>&1
```

## Scraper 2: AnyIOT Healthcheck

`anyiot_healthcheck.py` controlla la pagina:

```text
http://theoiziruam.ddns.net:808/index2.php
```

Lo script estrae i sensori temperatura/umidita e usa il timestamp dell'ultimo aggiornamento come heartbeat.

Logica di allarme:

- al momento vengono monitorati solo i sensori della casa `Cusago`
- i sensori `Zappardino` / Sicilia sono ignorati per evitare falsi allarmi quando vengono spenti
- i sensori dovrebbero aggiornare ogni 30 minuti
- un sensore e considerato non aggiornato dopo 45 minuti
- Telegram viene avvisato solo in caso di problemi

Invia notifica se:

- la pagina AnyIOT non e raggiungibile
- non viene estratto nessun sensore
- uno o piu sensori temperatura/umidita non aggiornano da oltre 45 minuti
- tutti i sensori risultano non aggiornati

Non invia notifica quando tutto e OK.

Esecuzione:

```bash
./run_anyiot_healthcheck.sh
```

Oppure direttamente:

```bash
python anyiot_healthcheck.py
```

Cron suggerito, ogni 30 minuti:

```cron
*/30 * * * * cd $HOME/meteoAgent && ./run_anyiot_healthcheck.sh >> $HOME/meteoAgent/anyiot_healthcheck.log 2>&1
```

## Configurazione Telegram

Copia `.env.example` in `.env`:

```bash
cp .env.example .env
```

Inserisci i valori reali:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_RECEIVER_ID=your_telegram_chat_id
```

Il file `.env` contiene dati sensibili ed e escluso dal repository tramite `.gitignore`.

## Installazione su Raspberry/Linux

```bash
cd ~
git clone https://github.com/martale1/meteoAgent.git
cd meteoAgent
cp .env.example .env
nano .env
chmod +x run_meteo.sh run_anyiot_healthcheck.sh
```

I launcher creano automaticamente `.venv` e installano le dipendenze da `requirements.txt` se necessario.

Prima esecuzione meteo:

```bash
./run_meteo.sh
```

Prima esecuzione healthcheck:

```bash
./run_anyiot_healthcheck.sh
```

## Installazione su Windows/Conda

Con ambiente Conda `openaiAgent`:

```powershell
& "C:\Users\theoi\anaconda3\Scripts\conda.exe" run -n openaiAgent pip install -r requirements.txt
```

Meteo:

```powershell
& "C:\Users\theoi\anaconda3\Scripts\conda.exe" run -n openaiAgent python ilmeteo_gioiosa.py
```

AnyIOT:

```powershell
& "C:\Users\theoi\anaconda3\Scripts\conda.exe" run -n openaiAgent python anyiot_healthcheck.py
```

## Script di supporto

- `inspect_available_days.py`: verifica i giorni disponibili su iLMeteo
- `inspect_day_ilmeteo.py`: ispezione della tabella meteo giornaliera
- `inspect_ilmeteo.py`: ispezione della pagina meteo principale
- `inspect_mare_ilmeteo.py`: ispezione della pagina mare
- `inspect_anyiot.py`: ispezione della pagina AnyIOT

## Note

I siti sorgente possono cambiare struttura HTML nel tempo. Se uno scraper smette di funzionare, usa gli script `inspect_*` per verificare rapidamente selettori, tabelle e blocchi disponibili.
