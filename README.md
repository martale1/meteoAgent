# meteoAgent

Scraper Python per le previsioni di Gioiosa Marea da iLMeteo.it.

Lo script estrae i 7 giorni disponibili dalla pagina principale, legge i dati orari dei singoli giorni e genera:

- `gioiosa_marea_ilmeteo.csv`: riepilogo giornaliero.
- `gioiosa_marea_orario_ilmeteo.csv`: dettaglio ora per ora.
- Messaggio Telegram formattato con temperature, onde, vento e direzioni.

## Configurazione

Copia `.env.example` in `.env` e inserisci:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_RECEIVER_ID=...
```

Il file `.env` non viene tracciato da Git.

## Esecuzione

```powershell
& "C:\Users\theoi\anaconda3\Scripts\conda.exe" run -n openaiAgent python ilmeteo_gioiosa.py
```

## Dipendenze

```powershell
pip install -r requirements.txt
```
