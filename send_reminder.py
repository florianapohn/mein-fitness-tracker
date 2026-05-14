import smtplib
import pandas as pd
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- SICHERE KONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
# TRAGE HIER DEINE GMAIL EIN:
SENDER_EMAIL = "deine-email@gmail.com" 
# Das Passwort wird sicher aus den GitHub Secrets geladen:
SENDER_PASSWORD = os.getenv("MAIL_PW") 

def send_email(recipient, subject, body):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Mail erfolgreich an {recipient} gesendet!")
    except Exception as e:
        print(f"Fehler beim Senden: {e}")

def check_reminders():
    # Prüfen, ob die Einstellungsdatei existiert
    if not os.path.exists("user_settings.csv"):
        print("Keine Einstellungsdatei gefunden. Bitte erstelle 'user_settings.csv' manuell auf GitHub.")
        return

    try:
        settings = pd.read_csv("user_settings.csv").iloc[0]
    except Exception as e:
        print(f"Fehler beim Lesen der Einstellungen: {e}")
        return

    if not settings['reminder_active']:
        print("Erinnerungen sind in den Einstellungen deaktiviert.")
        return

    today = datetime.now()
    wochentag_heute = today.strftime('%A') 
    
    # Mapping der Wochentage von Deutsch auf Englisch
    tage_map = {
        "Montag": "Monday", "Dienstag": "Tuesday", "Mittwoch": "Wednesday",
        "Donnerstag": "Thursday", "Freitag": "Friday", "Samstag": "Saturday", "Sonntag": "Sunday"
    }

    message = "Guten Morgen! ☀️\n\nZeit für deinen Check-in:\n\n"
    send_needed = False

    # Check: Tägliche Werte (Gewicht & Kalorien)
    if settings['weight_daily']:
        message += "- ⚖️ Gewicht & 🥗 Kalorien eintragen\n"
        send_needed = True

    # Check: Körpermaße (Wöchentlich am eingestellten Tag)
    if tage_map.get(settings['measures_day']) == wochentag_heute:
        message += "- 📏 Körpermaße messen (Hals, Brust, Bauch, Beine)\n"
        send_needed = True

    # BONUS: Manueller Test-Check (aus image_a2fce1.png)
    # Wenn du bei GitHub auf "Run Workflow" klickst, wird das Event "workflow_dispatch" gefeuert.
    if os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch":
        send_needed = True
        message += "\n(Dies ist ein manueller Test-Versand von GitHub aus)\n"

    if send_needed:
        message += "\nBleib dran! Hier geht's zu deiner App: https://mein-fitness-tracker.streamlit.app"
        send_email(settings['email'], "⏰ Dein Fitness-Reminder", message)
    else:
        print(f"Heute ({wochentag_heute}) steht laut Plan keine Erinnerung an.")

if __name__ == "__main__":
    check_reminders()
