# Guida Deployment - Generatore Etichette DYMO

Questa guida spiega come deployare l'applicazione web su Streamlit Cloud (GRATIS).

## 📋 Prerequisiti

1. Account GitHub (gratuito)
2. Repository GitHub con il codice
3. Account Streamlit Cloud (gratuito, login con GitHub)

## 🚀 Step 1: Preparare il Repository

Il repository è già pronto! Assicurati che questi file siano presenti:

- ✅ `app.py` - Applicazione Streamlit
- ✅ `utils.py` - Funzioni utilities
- ✅ `requirements.txt` - Dipendenze Python
- ✅ `template_update.dymo` - Template DYMO (IMPORTANTE!)
- ✅ `.streamlit/config.toml` - Configurazione Streamlit

### File da NON committare:
- ❌ `data_test.xlsx` (dati sensibili)
- ❌ `.venv/` (virtual environment)
- ❌ `out/` (file generati)

## 🌐 Step 2: Push su GitHub

Se non l'hai già fatto:

```bash
# Verifica stato git
git status

# Aggiungi tutti i file necessari
git add .

# Crea commit
git commit -m "Add Streamlit web app for DYMO label generation"

# Aggiungi remote (sostituisci con il tuo repository)
git remote add origin https://github.com/TUO-USERNAME/dymo-labels.git

# Push
git push -u origin main
```

## ☁️ Step 3: Deploy su Streamlit Cloud

### 3.1 Accedi a Streamlit Cloud

1. Vai su [share.streamlit.io](https://share.streamlit.io)
2. Clicca "Sign in" e accedi con il tuo account GitHub
3. Autorizza Streamlit ad accedere ai tuoi repository

### 3.2 Crea Nuova App

1. Clicca su "New app" (o "Create app")
2. Compila i campi:
   - **Repository:** Seleziona il tuo repository GitHub
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** Scegli un nome personalizzato (es: `bamboom-dymo-labels`)

3. Clicca "Deploy!"

### 3.3 Attendi il Deploy

- Il deploy richiede 2-5 minuti
- Streamlit installerà automaticamente le dipendenze da `requirements.txt`
- Vedrai i log in tempo reale

### 3.4 App Pronta!

Una volta completato, la tua app sarà disponibile all'URL:
```
https://TUO-APP-NAME.streamlit.app
```

## ⚙️ Configurazione Avanzata (Opzionale)

### Secrets Management

Se in futuro vorrai aggiungere un codice di accesso:

1. Nel dashboard Streamlit Cloud, vai su "Settings" > "Secrets"
2. Aggiungi:
```toml
ACCESS_CODE = "il-tuo-codice-segreto"
```

3. Modifica `app.py` per usare:
```python
import streamlit as st

# Controllo accesso
if 'authenticated' not in st.session_state:
    access_code = st.text_input("Codice Accesso", type="password")
    if access_code == st.secrets.get("ACCESS_CODE", ""):
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()
```

### Custom Domain (Opzionale - Richiede piano a pagamento)

Streamlit Cloud permette di usare un dominio personalizzato nei piani a pagamento.

## 🔄 Aggiornamenti

Per aggiornare l'app:

1. Modifica il codice localmente
2. Commit e push su GitHub:
```bash
git add .
git commit -m "Update: descrizione modifiche"
git push
```

3. Streamlit Cloud rileverà automaticamente i cambiamenti e rifarà il deploy

## 🐛 Troubleshooting

### App non si avvia

1. Controlla i log nel dashboard Streamlit Cloud
2. Verifica che `requirements.txt` sia corretto
3. Assicurati che `template_update.dymo` sia nel repository

### Errore "Template non trovato"

- Il file `template_update.dymo` DEVE essere committato nel repository
- Verifica che non sia in `.gitignore`
- Controlla il nome del file (è case-sensitive)

### Limite upload file

- Default: 200MB
- Modificabile in `.streamlit/config.toml` (max 200MB free tier)

### App lenta o in "sleep"

- Le app gratuite vanno in "sleep" dopo inattività
- Si risvegliano al primo accesso (30-60 secondi)
- Per avere app sempre attiva, considera piano Creator ($20/mese)

## 📊 Monitoraggio

Nel dashboard Streamlit Cloud puoi vedere:

- 📈 Statistiche di utilizzo
- 🔍 Logs in tempo reale
- ⚡ Performance metrics
- 👥 Numero di visitatori

## 💡 Best Practices

1. **Testa localmente prima del deploy:**
   ```bash
   streamlit run app.py
   ```

2. **Usa branch per test:**
   - `main` → produzione
   - `dev` → sviluppo/test

3. **Verifica limiti Free Tier:**
   - 1 app privata GRATIS
   - App pubbliche illimitate GRATIS
   - CPU e RAM limitati (sufficiente per questo uso)

## 🆘 Supporto

- 📚 [Documentazione Streamlit](https://docs.streamlit.io)
- 💬 [Forum Community](https://discuss.streamlit.io)
- 🐛 [GitHub Issues](https://github.com/streamlit/streamlit/issues)

## 🎉 Fatto!

La tua app è online e pronta all'uso! Condividi l'URL con chi deve usarla.

Per test locale:
```bash
streamlit run app.py
```

Per vedere l'app online:
```
https://TUO-APP-NAME.streamlit.app
```
