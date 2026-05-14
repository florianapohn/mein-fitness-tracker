import smtplib
import pandas as pd
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- KONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "deine-email@gmail.com" # Deine Gmail
SENDER_PASSWORD = "dein-app-passwort" # Dein Google App-Passwort

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
    if not os.path.exists("user_settings.csv"):
        return

    settings = pd.read_csv("user_settings.csv").iloc[0]
    if not settings['reminder_active']:
        return

    today = datetime.now()
    wochentag_heute = today.strftime('%A') # z.B. "Thursday"
    # Mapping für deutsche Wochentage aus der App
    tage_map = {
        "Montag": "Monday", "Dienstag": "Tuesday", "Mittwoch": "Wednesday",
        "Donnerstag": "Thursday", "Freitag": "Friday", "Samstag": "Saturday", "Sonntag": "Sunday"
    }

    message = "Guten Morgen! Zeit für deinen Check-in:\n\n"
    send_needed = False

    # Check: Tägliche Werte
    if settings['weight_daily']:
        message += "- ⚖️ Gewicht & 🥗 Kalorien eintragen\n"
        send_needed = True

    # Check: Körpermaße (z.B. jeden Donnerstag)
    if tage_map.get(settings['measures_day']) == wochentag_heute:
        message += "- 📏 Körpermaße messen (Hals, Brust, Bauch, Beine)\n"
        send_needed = True

    if send_needed:
        message += "\nHier geht's zu deiner App: [DEIN-STREAMLIT-LINK]"
        send_email(settings['email'], "⏰ Dein Fitness-Reminder", message)

if __name__ == "__main__":
    check_reminders()
