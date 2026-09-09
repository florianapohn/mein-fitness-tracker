# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import text
import numpy as np

try:
    from sklearn.linear_model import LinearRegression
    sklearn_available = True
except:
    sklearn_available = False

# --- DEUTSCHE ZAHLENFORMATIERUNG ---
def fmt_int(val):
    try:
        return f"{int(val):,}".replace(",", ".")
    except:
        return "0"

def fmt_dec(val):
    try:
        return f"{float(val):.1f}".replace(".", ",")
    except:
        return "0,0"

# --- RECHNER FÜR BMR & ERHALTUNGSKALORIEN (Mifflin-St. Jeor) ---
def calculate_tdee(weight_kg, height_cm, birthday_date, activity_level="Moderat"):
    today = date.today()
    age = today.year - birthday_date.year - ((today.month, today.day) < (birthday_date.month, birthday_date.day))
    
    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    
    pal_factors = {
        "Wenig (Sitzend / Urlaub)": 1.2,
        "Leicht (Spaziergänge, Büro)": 1.375,
        "Moderat (10k Schritte / Sport)": 1.55,
        "Hoch (Sehr aktiv)": 1.725
    }
    pal = pal_factors.get(activity_level, 1.4)
    return int(bmr * pal)

# --- REFEED MENÜPLAN GENERATOR ---
def get_refeed_plan(tdee):
    p1 = int(tdee * 0.25)
    p2 = int(tdee * 0.35)
    p3 = int(tdee * 0.30)
    snack = tdee - (p1 + p2 + p3)

    plan = {
        "Tag 1": [
            {"Mahlzeit": "Frühstück", "Name": "Haferflocken mit Beeren & Magerquark", "Kcal": p1, "Details": "80g Haferflocken, 200g Magerquark, 100g Beeren, 1TL Honig"},
            {"Mahlzeit": "Mittagessen", "Name": "Hähnchenbrust mit Reis & Brokkoli", "Kcal": p2, "Details": "200g Hähnchenbrust, 80g Reis (Rohgewicht), 200g Brokkoli, 1 EL Olivenöl"},
            {"Mahlzeit": "Abendessen", "Name": "Omelett mit Vollkornbrot & Salat", "Kcal": p3, "Details": "3 Eier, 2 Scheiben Vollkornbrot, großer gemischter Salat mit Essig/Öl"},
            {"Mahlzeit": "Snack", "Name": "Apfel & Handvoll Mandeln", "Kcal": snack, "Details": "1 großer Apfel, 20g Mandeln"}
        ],
        "Tag 2": [
            {"Mahlzeit": "Frühstück", "Name": "Vollkorn-Toast mit Avocado & Hüttenkäse", "Kcal": p1, "Details": "2 Scheiben Vollkornbrot, 1/2 Avocado, 150g Hüttenkäse, Tomatenscheiben"},
            {"Mahlzeit": "Mittagessen", "Name": "Lachsfillet mit Kartoffeln & Spargel/Grünzeug", "Kcal": p2, "Details": "180g Lachs, 250g gekochte Kartoffeln, 200g Gemüsemischung"},
            {"Mahlzeit": "Abendessen", "Name": "Magerquark-Bowl mit Banane & Nüssen", "Kcal": p3, "Details": "300g Magerquark, 1 Banane, 15g Walnüsse, Schuss Mineralwasser zum Anrühren"},
            {"Mahlzeit": "Snack", "Name": "Protein-Shake / Beeren-Smoothie", "Kcal": snack, "Details": "30g Whey Protein, 250ml Milch oder Pflanzendrink, 50g Beeren"}
        ],
        "Tag 3": [
            {"Mahlzeit": "Frühstück", "Name": "Griechischer Joghurt mit Banane & Zimt-Hafer", "Kcal": p1, "Details": "250g Griechischer Joghurt (5%), 1 Banane, 50g Haferflocken, Zimt"},
            {"Mahlzeit": "Mittagessen", "Name": "Puten-Chili mit Bohnen & Mais", "Kcal": p2, "Details": "200g Putenhack, 1/2 Dose Kidneybohnen, 1/2 Dose Mais, Passierte Tomaten"},
            {"Mahlzeit": "Abendessen", "Name": "Thunfisch-Salat mit Kartoffelecken", "Kcal": p3, "Details": "1 Dose Thunfisch im eigenen Saft, 200g Ofenkartoffeln, Blattsalat, Gurke"},
            {"Mahlzeit": "Snack", "Name": "Reiswaffeln mit Bitterschokolade / Hüttenkäse", "Kcal": snack, "Details": "3 Reiswaffeln, 100g Hüttenkäse oder 20g Zartbitterschokolade"}
        ]
    }
    
    shopping_list = [
        " Haferflocken (500g)", " Magerquark (1 kg)", " Griechischer Joghurt", " Beeren (TK oder frisch)", 
        " Bananen & Äpfel", " Hähnchenbrust / Putenhack (600g)", " Lachsfilet (200g)", " Thunfisch (1 Dose)",
        " Eier (6er Pack)", " Reis (1 Beutel)", " Kartoffeln (1 kg)", " Vollkornbrot", 
        " Brokkoli & Gemüsemischung", " Avocado", " Hüttenkäse", " Mandeln / Walnüsse"
    ]
    return plan, shopping_list

# --- ADAPTIVER TAGES-COACH & EMPFEHLUNGS-ENGINE ---
def generate_daily_recommendation(yesterday_row, target_kcal, base_steps=10000):
    steps_yesterday = int(yesterday_row['Schritte']) if 'Schritte' in yesterday_row and pd.notna(yesterday_row['Schritte']) else 0
    kcal_in_yesterday = int(yesterday_row['Kalorien_In']) if 'Kalorien_In' in yesterday_row and pd.notna(yesterday_row['Kalorien_In']) else 0
    
    rec = {
        "title": "🌟 Dein Tages-Briefing & Fahrplan",
        "steps_target": base_steps,
        "kcal_target": target_kcal,
        "snack_recommendation": "",
        "advice_text": "",
        "badge": "🎯 Normales Tagesziel"
    }
    
    # Szenario 1: Schrittziel stark übertroffen (>= 12.000) & wenig gegessen
    if steps_yesterday >= 12000 and (kcal_in_yesterday < target_kcal - 200 or kcal_in_yesterday == 0):
        reduced_steps = max(6000, base_steps - 2000)
        rec["steps_target"] = reduced_steps
        rec["kcal_target"] = target_kcal + 200
        rec["badge"] = "🔥 Regeneration & Power-Snack"
        rec["snack_recommendation"] = "💡 **Food-Tipp:** Gönn dir heute z.B. Hähnchen mit Reis & Gemüse oder eine Schüssel Naturjoghurt mit Apfel, Nüssen und etwas Honig."
        rec["advice_text"] = (
            f"Starke Leistung gestern! Du bist stolze **{fmt_int(steps_yesterday)} Schritte** gegangen und hattest ein hohes Defizit.\n\n"
            f"Damit dein Stoffwechsel aktiv bleibt und deine Muskeln regenerieren, kannst du es heute etwas ruhiger angehen lassen:\n"
            f"- **Schrittziel heute:** {fmt_int(reduced_steps)} Schritte (-2.000 Schritte Ausgleich)\n"
            f"- **Kalorienziel heute:** {fmt_int(target_kcal + 200)} kcal (+200 kcal Bonus)\n\n"
            f"{rec['snack_recommendation']}"
        )
    # Szenario 2: Schrittziel übertroffen
    elif steps_yesterday >= 12000:
        reduced_steps = max(7000, base_steps - 1000)
        rec["steps_target"] = reduced_steps
        rec["badge"] = "🏃‍♂️ Fleiß-Bonus"
        rec["snack_recommendation"] = "💡 **Food-Tipp:** Naturjoghurt mit einem gewürfelten Apfel & Zimt als perfekter Zwischensnack."
        rec["advice_text"] = (
            f"Gestern war ein super aktiver Tag ({fmt_int(steps_yesterday)} Schritte)! "
            f"Heute reicht ein entspannteres Ziel von **{fmt_int(reduced_steps)} Schritten**.\n\n"
            f"{rec['snack_recommendation']}"
        )
    # Szenario 3: Sehr wenig Schritte oder üppiges Essen gestern
    elif steps_yesterday < 6000 or kcal_in_yesterday > target_kcal + 300:
        boosted_steps = base_steps + 2000
        rec["steps_target"] = boosted_steps
        rec["badge"] = "⚡ Aktivitäts-Boost"
        rec["snack_recommendation"] = "💡 **Ernährungstipp:** Setze heute auf mageres Eiweiß (z.B. Hähnchenbrust, Magerquark) und mache ab 19:00 Uhr Schluss mit Snacken."
        rec["advice_text"] = (
            f"Gestern war ein etwas ruhigerer oder üppigerer Tag. Kein Problem – genau dafür ist dein Ausgleichstag da!\n\n"
            f"- **Schrittziel heute:** {fmt_int(boosted_steps)} Schritte (+2.000 Schritte Extra)\n"
            f"- **Kalorienziel heute:** {fmt_int(target_kcal)} kcal\n\n"
            f"{rec['snack_recommendation']}"
        )
    # Szenario 4: Standard / Solider Tag
    else:
        rec["snack_recommendation"] = "💡 **Food-Tipp:** Ausgewogene Mahlzeit mit Pute/Hähnchen, komplexe Kohlenhydrate (Reis/Kartoffeln) und viel Gemüse."
        rec["advice_text"] = (
            f"Gestern war ein solider Tag! Bleib genau auf diesem Kurs.\n\n"
            f"- **Schrittziel heute:** {fmt_int(base_steps)} Schritte\n"
            f"- **Kalorienziel heute:** {fmt_int(target_kcal)} kcal\n\n"
            f"{rec['snack_recommendation']}"
        )
        
    return rec

# --- E-MAIL VERSAND FUNKTION ---
def send_reminder_email(to_email, subject, body_text):
    try:
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]
        sender_email = st.secrets["email"]["sender_email"]
        sender_password = st.secrets["email"]["sender_password"]
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"E-Mail Fehler: {e}")
        return False

# --- LOGIN SYSTEM ---
def check_password():
    def password_entered():
        correct_username = st.secrets["login"]["username"]
        correct_password = st.secrets["login"]["password"]
        if st.session_state["username"] == correct_username and st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Login zum Fitness Hub")
        st.text_input("Benutzername", key="username")
        st.text_input("Passwort", type="password", key="password")
        st.button("Anmelden", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 Login zum Fitness Hub")
        st.text_input("Benutzername", key="username")
        st.text_input("Passwort", type="password", key="password")
        st.button("Anmelden", on_click=password_entered)
        st.error("😕 Benutzername oder Passwort falsch")
        return False
    return True

if check_password():

    # --- APP KONFIGURATION ---
    st.set_page_config(page_title="My Fitness Hub", layout="wide")
    st.title("My All-in-One Fitness Hub 🚀")

    # --- CLOUD DATENBANK-ANSCHLUSS ---
    conn = st.connection("local_db", type="sql")

    with conn.session as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS fitness_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Datum TEXT, Uhrzeit TEXT, Gewicht REAL, Schritte INTEGER, 
                Aktivzeit INTEGER, Kalorien_In INTEGER, Kalorien_Out INTEGER, 
                Hals REAL, Brust REAL, Bauch REAL, Oberschenkel REAL, 
                Aktivitaet TEXT, Bemerkung TEXT,
                Eiweiss REAL DEFAULT 0.0,
                Wasser_Menge INTEGER DEFAULT 0,
                Koerperfett REAL DEFAULT 0.0,
                Muskelmasse REAL DEFAULT 0.0,
                Koerperwasser REAL DEFAULT 0.0
            )
        """))
        try:
            session.execute(text('ALTER TABLE fitness_data ADD COLUMN Eiweiss REAL DEFAULT 0.0'))
            session.commit()
        except: pass
        try:
            session.execute(text('ALTER TABLE fitness_data ADD COLUMN "Koerperwasser" REAL DEFAULT 0.0'))
            session.commit()
        except: pass
        try:
            session.execute(text('ALTER TABLE fitness_data ADD COLUMN "Muskelmasse" REAL DEFAULT 0.0'))
            session.commit()
        except: pass
        
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS user_settings (
                key TEXT PRIMARY KEY, value TEXT
            )
        """))
        session.commit()

    def load_fitness_data():
        cols = ['Datum', 'Uhrzeit', 'Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Aktivitaet', 'Bemerkung', 'Eiweiss', 'Wasser_Menge', 'Koerperfett', 'Muskelmasse', 'Koerperwasser']
        try:
            df_sql = conn.query("SELECT * FROM fitness_data", ttl=0)
            if df_sql.empty:
                return pd.DataFrame(columns=cols)
            
            df_sql.columns = [c.lower() for c in df_sql.columns]
            
            df_sql = df_sql.rename(columns={
                'datum': 'Datum', 'uhrzeit': 'Uhrzeit', 'gewicht': 'Gewicht', 
                'schritte': 'Schritte', 'aktivzeit': 'Aktivzeit', 'kalorien_in': 'Kalorien_In', 
                'kalorien_out': 'Kalorien_Out', 'hals': 'Hals', 'brust': 'Brust', 
                'bauch': 'Bauch', 'oberschenkel': 'Oberschenkel', 'aktivitaet': 'Aktivitaet', 
                'bemerkung': 'Bemerkung', 'eiweiss': 'Eiweiss', 'wasser_menge': 'Wasser_Menge', 
                'koerperfett': 'Koerperfett', 'muskelmasse': 'Muskelmasse', 'koerperwasser': 'Koerperwasser'
            })
            
            df_sql['Datum'] = pd.to_datetime(df_sql['Datum'])
            if 'id' in df_sql.columns: 
                df_sql = df_sql.drop(columns=['id'])
            
            for c in ['Wasser_Menge', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out']:
                if c in df_sql.columns: df_sql[c] = df_sql[c].fillna(0).astype(int)
            for c in ['Eiweiss', 'Koerperfett', 'Muskelmasse', 'Koerperwasser', 'Gewicht', 'Hals', 'Brust', 'Bauch', 'Oberschenkel']:
                if c in df_sql.columns: df_sql[c] = df_sql[c].fillna(0.0).astype(float)
            
            return df_sql
        except:
            return pd.DataFrame(columns=cols)

    def load_settings():
        default_settings = {
            "email": "florian.pohn@protonmail.com", "reminder_active": "False", 
            "weight_daily": "True", "measures_day": "Donnerstag", "height": "179", 
            "target_weight": "85.0", "birthday": "1990-01-01", "last_email_kw": "0",
            "maintenance_kcal": "2300", "deficit_mode": "Moderate", "custom_target_kcal": "2000",
            "refeed_start_date": "", "last_daily_mail_date": "", "last_inactivity_mail_date": ""
        }
        try:
            df_set = conn.query("SELECT * FROM user_settings", ttl=0)
            if df_set.empty: return default_settings
            res = dict(zip(df_set['key'], df_set['value']))
            for k, v in default_settings.items():
                if k not in res: res[k] = v
            return res
        except:
            return default_settings

    def save_settings_to_db(s_dict):
        with conn.session as session:
            for k, v in s_dict.items():
                session.execute(text("INSERT OR REPLACE INTO user_settings (key, value) VALUES (:k, :v)"), {"k": k, "v": str(v)})
            session.commit()

    df = load_fitness_data()
    settings = load_settings()

    settings["height"] = int(settings.get("height", 179))
    settings["target_weight"] = float(settings.get("target_weight", 85.0))
    settings["reminder_active"] = settings.get("reminder_active") == "True"
    settings["last_email_kw"] = int(settings.get("last_email_kw", 0))
    settings["maintenance_kcal"] = int(settings.get("maintenance_kcal", 2300))
    settings["custom_target_kcal"] = int(settings.get("custom_target_kcal", 2000))

    df_filled = df.sort_values(['Datum', 'Uhrzeit']).copy() if not df.empty else pd.DataFrame()
    if not df.empty:
        cols_to_fill = ['Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Gewicht', 'Koerperfett', 'Muskelmasse', 'Koerperwasser']
        for col in cols_to_fill:
            df_filled[col] = df_filled[col].replace(0, pd.NA)
            df_filled[col] = df_filled[col].ffill().fillna(0)

    limit_kcal = settings["custom_target_kcal"]

    # --- EMAIL & AUTOMATION LOGIK ---
    if "email" in st.secrets and settings.get("reminder_active", False):
        heute = date.today()
        heute_str = heute.strftime("%Y-%m-%d")
        
        # 1. TÄGLICHES MORGEN-BRIEFING PER E-MAIL
        if settings.get("last_daily_mail_date") != heute_str and not df_filled.empty:
            yesterday_dt = pd.Timestamp(heute - timedelta(days=1))
            df_yesterday = df_filled[df_filled['Datum'].dt.date == yesterday_dt.date()]
            
            if not df_yesterday.empty:
                y_row = df_yesterday.iloc[-1]
                rec_mail = generate_daily_recommendation(y_row, limit_kcal)
                
                mail_subject = f"☀️ Dein Tages-Coach: {rec_mail['badge']}"
                mail_body = f"Hallo Florian!\n\nHier ist deine persönliche Empfehlung für den heutigen Tag:\n\n"
                mail_body += f"{rec_mail['advice_text'].replace('**', '').replace('💡 ', '')}\n\n"
                mail_body += f"Bleib dran und erreiche dein Ziel von {settings['target_weight']} kg!\n\nDein Fitness Hub Coach 🚀"
                
                if send_reminder_email(settings.get("email"), mail_subject, mail_body):
                    settings["last_daily_mail_date"] = heute_str
                    save_settings_to_db(settings)
                    st.sidebar.success("🌅 Tages-Briefing E-Mail gesendet!")

        # 2. INAKTIVITÄTS-REMINDER NACH 7 TAGEN
        if not df_filled.empty:
            last_entry_date = df_filled['Datum'].max().date()
            days_inactive = (heute - last_entry_date).days
            
            if days_inactive >= 7 and settings.get("last_inactivity_mail_date") != heute_str:
                mail_subject = "🔥 Vermisse dich! Zeit für deinen Comeback-Start 🚀"
                mail_body = (
                    f"Hallo Florian!\n\n"
                    f"Du hast seit {days_inactive} Tagen keinen Eintrag mehr in deinem Fitness Hub gemacht.\n"
                    f"Kein Stress – Rückschläge oder Pausen gehören dazu! Das Wichtigste ist, jetzt einfach wieder einzusteigen.\n\n"
                    f"💪 'Erfolg ist die Summe kleiner Anstrengungen, die sich Tag für Tag wiederholen.'\n\n"
                    f"Trag heute einfach kurz dein Gewicht oder deine Schritte ein und bleib am Ball zu deinen {settings['target_weight']} kg!\n\n"
                    f"Dein Fitness Hub Coach 🚀"
                )
                if send_reminder_email(settings.get("email"), mail_subject, mail_body):
                    settings["last_inactivity_mail_date"] = heute_str
                    save_settings_to_db(settings)
                    st.sidebar.info("📧 Inaktivitäts-Erinnerung gesendet!")

        # 3. WÖCHENTLICHE MESSUNGS-ERINNERUNG
        wochentage_dict = {"Montag": 0, "Dienstag": 1, "Mittwoch": 2, "Donnerstag": 3, "Freitag": 4, "Samstag": 5, "Sonntag": 6}
        ziel_wochentag = wochentage_dict.get(settings.get("measures_day", "Donnerstag"), 3)
        aktuelle_kw = heute.isocalendar()[1]
        
        if heute.weekday() == ziel_wochentag and settings["last_email_kw"] != aktuelle_kw and not df_filled.empty:
            latest_mail_row = df_filled.iloc[-1]
            mail_text = f"Hallo Florian!\n\nHier ist deine wöchentliche Erinnerung vom My Fitness Hub.\n\n"
            mail_text += f"Aktueller Stand deiner letzten Messungen:\n"
            mail_text += f"- Gewicht: {latest_mail_row['Gewicht']:.1f} kg\n"
            mail_text += f"- Bauchumfang: {latest_mail_row['Bauch']:.1f} cm\n"
            mail_text += f"- Brustumfang: {latest_mail_row['Brust']:.1f} cm\n"
            mail_text += f"- Halsumfang: {latest_mail_row['Hals']:.1f} cm\n"
            mail_text += f"- Oberschenkel: {latest_mail_row['Oberschenkel']:.1f} cm\n"
            mail_text += "\nBleib dran! 🏆"
            
            if send_reminder_email(settings.get("email"), "My Fitness Hub - Wöchentlicher Check-In", mail_text):
                settings["last_email_kw"] = aktuelle_kw
                save_settings_to_db(settings)
                st.sidebar.success("📧 Erinnerungs-Mail gesendet!")

    # --- 4. SEITENLEISTE: DATENEINGABE ---
    st.sidebar.header(f"Hallo Florian!")
    
    if st.sidebar.button("🌴 Nach dem Urlaub / Plateau-Breaker", type="primary"):
        st.session_state["show_refeed_modal"] = True

    with st.sidebar.form("entry_form", clear_on_submit=True):
        d = st.date_input("Datum auswählen", date.today())
        sport_options = ["Kein Sport", "Gehen", "Fahrrad", "Schwimmen", "Krafttraining"]
        act_type = st.select_slider("Welchen Sport hast du heute gemacht?", options=sport_options, value="Gehen")
        
        st.subheader("📊 Waagen-Analyse")
        wc1, wc2 = st.columns(2)
        gew = wc1.number_input("Gewicht (kg)", format="%.1f", min_value=0.0, value=None, placeholder="z.B. 75,2")
        in_fat = wc2.number_input("Körperfett (%)", format="%.1f", min_value=0.0, max_value=100.0, step=0.1, value=None, placeholder="z.B. 15,4")
        in_musc = wc1.number_input("Muskeln (kg)", format="%.1f", min_value=0.0, max_value=200.0, step=0.1, value=None, placeholder="z.B. 34,2")
        in_water = wc2.number_input("Körperwasser (%)", format="%.1f", min_value=0.0, max_value=100.0, step=0.1, value=None, placeholder="z.B. 55,1")
        
        st.subheader("🏃‍♂️ Aktivität")
        ac1, ac2 = st.columns(2)
        step = ac1.number_input("Schritte", step=100, min_value=0, value=None, placeholder="z.B. 10000")
        k_out = ac2.number_input("Kalorien (Out)", step=50, min_value=0, value=None, placeholder="z.B. 400")
        akt_min = st.number_input("Dauer (Minuten)", step=5, min_value=0, value=None, placeholder="z.B. 45")
        note = st.text_input("📝 Bemerkung", placeholder="Urlaub, Krank, Feier...")
        
        st.subheader("🍗 Ernährung & Tracking")
        ec1, ec2 = st.columns(2)
        k_in = ec1.number_input("Kalorien (In)", step=50, min_value=0, value=None, placeholder="z.B. 2100")
        in_eiweiss = ec2.number_input("Eiweiß am Tag (Gramm)", format="%.1f", min_value=0.0, value=None, placeholder="z.B. 112,5")
        in_wasser = st.number_input("Flüssigkeit am Tag (Gläser / Flaschen)", step=1, min_value=0, value=None, placeholder="z.B. 6")
        
        st.subheader("📏 Körpermaße (cm)")
        h1, h2 = st.columns(2)
        hals_in = h1.number_input("Hals", format="%.1f", value=None, placeholder="z.B. 38,0")
        brust_in = h2.number_input("Brust", format="%.1f", value=None, placeholder="z.B. 102,5")
        bauch_in = h1.number_input("Bauch", format="%.1f", value=None, placeholder="z.B. 88,0")
        bein_in = h2.number_input("Oberschenkel", format="%.1f", value=None, placeholder="z.B. 56,5")
        
        submit = st.form_submit_button("Speichern ✨")

    if submit:
        now_t = datetime.now().strftime("%H:%M")
        with conn.session as session:
            session.execute(text("""
                INSERT INTO fitness_data (Datum, Uhrzeit, Gewicht, Schritte, Aktivzeit, Kalorien_In, Kalorien_Out, Hals, Brust, Bauch, Oberschenkel, Aktivitaet, Bemerkung, Eiweiss, Wasser_Menge, Koerperfett, Muskelmasse, Koerperwasser)
                VALUES (:Datum, :Uhrzeit, :Gewicht, :Schritte, :Aktivzeit, :Kalorien_In, :Kalorien_Out, :Hals, :Brust, :Bauch, :Oberschenkel, :Aktivitaet, :Bemerkung, :Eiweiss, :Wasser_Menge, :Koerperfett, :Muskelmasse, :Koerperwasser)
            """), {
                "Datum": d.strftime("%Y-%m-%d"), "Uhrzeit": now_t, 
                "Gewicht": gew if gew is not None else 0.0, 
                "Schritte": step if step is not None else 0, 
                "Aktivzeit": akt_min if akt_min is not None else 0, 
                "Kalorien_In": k_in if k_in is not None else 0, 
                "Kalorien_Out": k_out if k_out is not None else 0, 
                "Hals": hals_in if hals_in is not None else 0.0, 
                "Brust": brust_in if brust_in is not None else 0.0, 
                "Bauch": bauch_in if bauch_in is not None else 0.0, 
                "Oberschenkel": bein_in if bein_in is not None else 0.0, 
                "Aktivitaet": act_type, "Bemerkung": note, 
                "Eiweiss": in_eiweiss if in_eiweiss is not None else 0.0, 
                "Wasser_Menge": in_wasser if in_wasser is not None else 0, 
                "Koerperfett": in_fat if in_fat is not None else 0.0, 
                "Muskelmasse": in_musc if in_musc is not None else 0.0, 
                "Koerperwasser": in_water if in_water is not None else 0.0
            })
            session.commit()
        st.session_state["active_tab"] = 0
        st.rerun()

    # --- 5. SEITENLEISTE: EINSTELLUNGEN ---
    st.sidebar.markdown("---")
    with st.sidebar.expander("⚙️ Profil & Zielgewicht"):
        new_h = st.number_input("Größe (cm)", value=settings["height"], step=1)
        try: stored_bday = datetime.strptime(str(settings.get("birthday", "1990-01-01")), "%Y-%m-%d").date()
        except: stored_bday = date(1990, 1, 1)
        new_bday = st.date_input("Geburtsdatum", value=stored_bday, min_value=date(1920, 1, 1), max_value=date.today())
        new_target = st.number_input("Zielgewicht (kg)", value=settings["target_weight"], format="%.1f", step=0.1)
        new_mail = st.text_input("E-Mail", value=settings.get("email", "florian.pohn@protonmail.com"))
        new_active = st.checkbox("E-Mail Aktiv", value=settings["reminder_active"])
        days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        try: day_idx = days.index(settings.get("measures_day", "Donnerstag"))
        except: day_idx = 3
        new_day = st.selectbox("Tag für Maße-Erinnerung", days, index=day_idx)
        
        if st.button("Speichern 💾"):
            updated_settings = {
                "email": new_mail, "reminder_active": new_active, "height": new_h, 
                "measures_day": new_day, "weight_daily": "True", "target_weight": new_target, 
                "birthday": new_bday.strftime("%Y-%m-%d"), "last_email_kw": settings["last_email_kw"],
                "maintenance_kcal": settings["maintenance_kcal"], "deficit_mode": settings.get("deficit_mode", "Moderate"),
                "custom_target_kcal": settings["custom_target_kcal"], "refeed_start_date": settings.get("refeed_start_date", ""),
                "last_daily_mail_date": settings.get("last_daily_mail_date", ""),
                "last_inactivity_mail_date": settings.get("last_inactivity_mail_date", "")
            }
            save_settings_to_db(updated_settings)
            st.success("Einstellungen gespeichert! ✅")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🚀 Erfolge teilen")
    if not df.empty:
        latest_all_f = df_filled.iloc[-1]
        h_m_f = float(settings["height"]) / 100
        bmi_val_f = float(latest_all_f['Gewicht']) / (h_m_f ** 2) if latest_all_f['Gewicht'] > 0 else 0.0
        last_7_f = df[df['Datum'] > (pd.Timestamp.now() - pd.Timedelta(days=7))]
        s_steps_f = last_7_f['Schritte'].sum() if 'Schritte' in last_7_f.columns else 0
        s_kcal_f = last_7_f['Kalorien_Out'].sum() if 'Kalorien_Out' in last_7_f.columns else 0
        s_km_f = s_steps_f / 1400
        if st.sidebar.button("Erfolg kopieren 📋"):
            st.sidebar.code(f"Hey, schau mal! 🏆\nGewicht: {fmt_dec(latest_all_f['Gewicht'])} kg\nBMI: {fmt_dec(bmi_val_f)}\n\nLetzte 7 Tage:\n🔥 {fmt_int(s_kcal_f)} kcal\n🏃‍♂️ {fmt_dec(s_km_f)} km\n👣 {fmt_int(s_steps_f)} Schritte", language="text")

    if st.sidebar.button("Logout 🚪"):
        st.session_state.clear()
        st.rerun()

    # --- POPUP / DIALOG: PLATEAU-BREAKER RECHNER ---
    if st.session_state.get("show_refeed_modal", False):
        st.markdown("### 🌴 Nach dem Urlaub: Erhaltungsbedarf & 3-Tage-Refeed")
        latest_w = df_filled.iloc[-1]['Gewicht'] if not df_filled.empty else 87.9
        
        with st.form("refeed_form"):
            c1, c2 = st.columns(2)
            curr_w = c1.number_input("Aktuelles Gewicht nach dem Urlaub (kg)", value=float(latest_w), format="%.1f")
            act_lvl = c2.selectbox("Aktivitätslevel im Alltag", ["Wenig (Sitzend / Urlaub)", "Leicht (Spaziergänge, Büro)", "Moderat (10k Schritte / Sport)", "Hoch (Sehr aktiv)"], index=2)
            
            submit_refeed = st.form_submit_button("Erhaltungsbedarf neu berechnen & 3-Tage-Plan aktivieren 🚀")
            
            if submit_refeed:
                try: stored_bday = datetime.strptime(str(settings.get("birthday", "1990-01-01")), "%Y-%m-%d").date()
                except: stored_bday = date(1990, 1, 1)
                
                m_kcal = calculate_tdee(curr_w, settings["height"], stored_bday, act_lvl)
                
                settings["maintenance_kcal"] = str(m_kcal)
                settings["custom_target_kcal"] = str(m_kcal)
                settings["refeed_start_date"] = date.today().strftime("%Y-%m-%d")
                save_settings_to_db(settings)
                
                st.session_state["show_refeed_modal"] = False
                st.success(f"✅ Neuberechnung erfolgreich! Dein Erhaltungsbedarf liegt bei **{m_kcal} kcal/Tag**.")
                st.rerun()
                
        if st.button("Abbrechen ❌"):
            st.session_state["show_refeed_modal"] = False
            st.rerun()
        st.markdown("---")

    # --- 6. HAUPTBEREICH & DASHBOARD COACH CARD ---
    if not df_filled.empty:
        df_daily = df_filled.groupby('Datum').agg({
            'Kalorien_In': 'sum', 'Kalorien_Out': 'sum', 'Schritte': 'sum', 'Gewicht': 'last', 
            'Hals': 'last', 'Brust': 'last', 'Bauch': 'last', 'Oberschenkel': 'last',
            'Eiweiss': 'sum', 'Wasser_Menge': 'sum', 'Koerperfett': 'last', 'Muskelmasse': 'last', 'Koerperwasser': 'last'
        }).reset_index()
        
        # Gestrige Zeile für Empfehlungen ermitteln
        yesterday_pd = pd.Timestamp(date.today() - timedelta(days=1))
        df_yesterday_check = df_daily[df_daily['Datum'].dt.date == yesterday_pd.date()]
        if not df_yesterday_check.empty:
            rec_today = generate_daily_recommendation(df_yesterday_check.iloc[-1], limit_kcal)
        else:
            rec_today = generate_daily_recommendation({}, limit_kcal)
            
        # COACH BOX DIREKT OBEN AUF DER HAUPTSEITE
        st.markdown(f"""
        <div style="background-color: #1a2634; border-left: 6px solid #00d2ff; padding: 18px; border-radius: 12px; margin-bottom: 20px;">
            <h3 style="margin:0; color:#00d2ff;">{rec_today['title']} <span style="font-size:14px; background:#00d2ff22; color:#00d2ff; padding:4px 10px; border-radius:15px; margin-left:10px;">{rec_today['badge']}</span></h3>
            <p style="margin:10px 0 0 0; font-size:15px; color:#e0e0e0; line-height:1.5;">
                {rec_today['advice_text'].replace('**', '<b>').replace('**', '</b>')}
            </p>
        </div>
        """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["Kurven & Trends 📈", "🔥 Plateau-Breaker & Coach", "Langzeit-Statistik 📊", "Datentabelle 📋"])

    with tab1:
        if not df_filled.empty:
            min_datum_in_db = df_daily['Datum'].min()
            ten_days_ago = pd.Timestamp.now() - pd.Timedelta(days=10)
            if min_datum_in_db < ten_days_ago:
                df_p = df_daily.sort_values('Datum')
            else:
                df_p = df_daily[df_daily['Datum'] >= ten_days_ago].sort_values('Datum')
                
            if df_p.empty: df_p = df_daily.tail(10)
            
            latest = df_p.iloc[-1]
            h_m = float(settings["height"]) / 100
            bmi_val = float(latest['Gewicht']) / (h_m ** 2) if latest['Gewicht'] > 0 else 0.0
            bmi_cat = "Normalgewicht" if 18.5 <= bmi_val < 25 else "Übergewicht" if 25 <= bmi_val < 30 else "Adipositas" if bmi_val >= 30 else "Untergewicht"
            target_w = float(settings["target_weight"])
            
            st.subheader("⚖️ Gewichtstrend & KI-Prognose")
            col_w_metric, col_w_graph = st.columns([0.25, 0.75])
            
            prognose_text = "Nicht genügend Wiege-Daten für KI-Prognose."
            fig_w = go.Figure()
            fig_w.add_trace(go.Scatter(x=df_p['Datum'], y=df_p['Gewicht'], fill='tozeroy', mode='lines+markers', name="Gewicht (Real)", line=dict(width=3, color='#0288D1', shape='spline')))
            
            df_w_valid = df_daily[df_daily['Gewicht'] > 0.1].copy()
            if sklearn_available and len(df_w_valid) >= 3:
                try:
                    first_date = df_w_valid['Datum'].min()
                    df_w_valid['Tage'] = (df_w_valid['Datum'] - first_date).dt.days
                    X = df_w_valid[['Tage']].values
                    y = df_w_valid['Gewicht'].values
                    
                    model = LinearRegression()
                    model.fit(X, y)
                    
                    future_days = 28
                    last_tag = df_w_valid['Tage'].max()
                    future_x = np.array([[last_tag], [last_tag + future_days]])
                    future_y = model.predict(future_x)
                    future_dates = [df_w_valid['Datum'].max(), df_w_valid['Datum'].max() + timedelta(days=future_days)]
                    
                    fig_w.add_trace(go.Scatter(x=future_dates, y=future_y, mode='lines', name="KI Trend (4 Wochen)", line=dict(dash='dash', color='magenta', width=3)))
                    steigung = model.coef_[0]
                    achsenabschnitt = model.intercept_
                    if steigung < 0:
                        tage_bis_ziel = (target_w - achsenabschnitt) / steigung
                        ziel_datum = first_date + timedelta(days=int(tage_bis_ziel))
                        if ziel_datum > datetime.now():
                            prognose_text = f"🔮 **KI-Prognose:** Bei gleichbleibendem Trend erreichst du dein Zielgewicht von {fmt_dec(target_w)} kg am **{ziel_datum.strftime('%d.%m.%Y')}**."
                        else:
                            prognose_text = "🔮 **KI-Prognose:** Du bist voll auf Kurs!"
                    elif steigung > 0:
                        prognose_text = "🔮 **KI-Prognose:** Das Gewicht steigt aktuell leicht an. Defizit prüfen! 📊"
                except:
                    prognose_text = "🔮 **KI-Prognose:** Berechnungsfehler. Füge mehr Daten hinzu."
            else:
                prognose_text = "🔮 **KI-Prognose:** Wird automatisch aktiv, sobald mindestens 3 Wiege-Einträge in der Tabelle stehen."
            
            with col_w_metric:
                st.metric("Aktuell", f"{fmt_dec(latest['Gewicht'])} kg", f"{fmt_dec(latest['Gewicht'] - target_w)} kg zum Ziel", delta_color="inverse")
                st.write("")
                st.markdown(prognose_text)
                
            with col_w_graph:
                fig_w.add_hline(y=target_w, line_dash="dash", line_color="red", annotation_text=f"Ziel {fmt_dec(target_w)}kg")
                fig_w.update_layout(height=300, margin=dict(l=0,r=0,t=20,b=0))
                st.plotly_chart(fig_w, use_container_width=True, config={'staticPlot': True})

            # --- GEWEBE-ANALYSE BEREICH ---
            st.markdown("---")
            st.subheader("🧬 Körperzusammensetzung")
            
            b_col1, b_col2, b_col3 = st.columns(3)
            with b_col1:
                df_valid_fat = df_daily[df_daily['Koerperfett'] > 0.1].sort_values('Datum')
                if not df_valid_fat.empty:
                    fig_fat = go.Figure(go.Scatter(x=df_valid_fat.tail(10)['Datum'], y=df_valid_fat.tail(10)['Koerperfett'], mode='lines+markers', name="Fett %", line=dict(color='#e74c3c', width=3)))
                    fig_fat.update_layout(height=220, margin=dict(l=0,r=0,t=20,b=0), title=f"📉 Körperfett-Verlauf (Aktuell: {fmt_dec(latest['Koerperfett'])} %)")
                    st.plotly_chart(fig_fat, use_container_width=True, config={'staticPlot': True})
                else:
                    st.info("Trage links Körperfett-Werte ein.")
            with b_col2:
                df_valid_water = df_daily[df_daily['Koerperwasser'] > 0.1].sort_values('Datum')
                if not df_valid_water.empty:
                    fig_water = go.Figure(go.Scatter(x=df_valid_water.tail(10)['Datum'], y=df_valid_water.tail(10)['Koerperwasser'], mode='lines+markers', name="Wasser %", line=dict(color='#3498db', width=3)))
                    fig_water.update_layout(height=220, margin=dict(l=0,r=0,t=20,b=0), title=f"💧 Körperwasser-Verlauf (Aktuell: {fmt_dec(latest['Koerperwasser'])} %)")
                    st.plotly_chart(fig_water, use_container_width=True, config={'staticPlot': True})
                else:
                    st.info("Trage links Körperwasser-Werte ein.")
            with b_col3:
                df_valid_musc = df_daily[df_daily['Muskelmasse'] > 0.1].sort_values('Datum')
                if not df_valid_musc.empty:
                    fig_musc = go.Figure(go.Scatter(x=df_valid_musc.tail(10)['Datum'], y=df_valid_musc.tail(10)['Muskelmasse'], mode='lines+markers', name="Muskeln kg", line=dict(color='#2ecc71', width=3)))
                    fig_musc.update_layout(height=220, margin=dict(l=0,r=0,t=20,b=0), title=f"💪 Muskelmasse-Verlauf (Aktuell: {fmt_dec(latest['Muskelmasse'])} kg)")
                    st.plotly_chart(fig_musc, use_container_width=True, config={'staticPlot': True})
                else:
                    st.info("Trage links Muskelmasse ein.")

            st.markdown("---")
            st.subheader("🥗 Kalorien-Haushalt")
            netto_kcal = int(latest['Kalorien_In'] - latest['Kalorien_Out'])
            diff_to_limit = int(limit_kcal - latest['Kalorien_In'])
            
            if netto_kcal <= (limit_kcal - 300):
                ampel_color = "#1e3d2f"
                ampel_text = "🟢 Optimales Defizit"
            elif (limit_kcal - 300) < netto_kcal <= limit_kcal:
                ampel_color = "#3a351c"
                ampel_text = "🟡 Grenzwertig / Haltekalorien"
            else:
                ampel_color = "#4c1c1c"
                ampel_text = "🔴 Kalorien-Überschuss!"
                
            c_m, c_g = st.columns([0.25, 0.75])
            with c_m:
                st.metric("Aufgenommen", f"{fmt_int(latest['Kalorien_In'])} kcal")
                st.metric(f"Übrig (vom Ziel: {limit_kcal} kcal)", f"{fmt_int(diff_to_limit)} kcal", delta_color="normal" if diff_to_limit >= 0 else "inverse")
                st.markdown(f"""
                <div style="background-color:{ampel_color}; padding:15px; border-radius:10px; border-left: 5px solid {'#2ecc71' if '🟢' in ampel_text else '#f1c40f' if '🟡' in ampel_text else '#e74c3c'};">
                    <p style="margin:0; font-size:12px; color:#aaa; font-weight:bold;">NETTO-BILANZ (IN-OUT)</p>
                    <h2 style="margin:0; color:white;">{fmt_int(netto_kcal)} kcal</h2>
                    <p style="margin:5px 0 0 0; font-size:14px; font-weight:bold;">{ampel_text}</p>
                </div>
                """, unsafe_allow_html=True)
                
            with c_g:
                fig_c = px.bar(df_p, x='Datum', y=['Kalorien_In', 'Kalorien_Out'], barmode='group')
                fig_c.add_hline(y=limit_kcal, line_dash="dot", line_color="red", annotation_text=f"Ziel {limit_kcal}")
                fig_c.update_layout(height=350, margin=dict(l=0,r=0,t=20,b=0))
                st.plotly_chart(fig_c, use_container_width=True, config={'staticPlot': True})

            st.markdown("---")
            st.subheader("🎯 Ernährungs-Fortschritt (Heute)")
            ef_col1, ef_col2 = st.columns(2)
            
            size_protein = 112
            aktuelles_protein = float(latest.get('Eiweiss', 0.0))
            protein_quote = min(int((aktuelles_protein / size_protein) * 100), 100) if aktuelles_protein > 0 else 0
            
            with ef_col1:
                st.markdown(f"**🍗 Proteine:** {fmt_dec(aktuelles_protein)}g von {size_protein}g ({protein_quote}%)")
                st.progress(protein_quote / 100)

            grid_wasser = 5
            aktuelles_wasser = int(latest.get('Wasser_Menge', 0))
            wasser_quote = min(int((aktuelles_wasser / grid_wasser) * 100), 100) if aktuelles_wasser > 0 else 0
            
            with ef_col2:
                st.markdown(f"**💧 Flüssigkeit:** {aktuelles_wasser} von {grid_wasser} Einheiten ({wasser_quote}%)")
                st.progress(wasser_quote / 100)

            st.markdown("---")
            st.subheader("👣 Tägliche Schritte & BMI")
            col_steps, col_bmi_gauge = st.columns([0.7, 0.3])
            with col_steps:
                fig_s = go.Figure(go.Bar(x=df_p['Datum'], y=df_p['Schritte'], marker_color='lightblue', text=df_p['Schritte'], textposition='outside'))
                fig_s.add_hline(y=rec_today.get("steps_target", 10000), line_dash="dash", line_color="white", annotation_text=f"Dynamisches Ziel: {rec_today.get('steps_target', 10000)}")
                fig_s.update_layout(height=350, margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig_s, use_container_width=True, config={'staticPlot': True})
            with col_bmi_gauge:
                st.markdown(f"<p style='text-align: center; margin-bottom: 0;'><b>{bmi_cat}</b></p>", unsafe_allow_html=True)
                fig_bmi = go.Figure(go.Indicator(mode="gauge+number", value=bmi_val, number={'valueformat': ".1f", 'font': {'size': 20}},
                    gauge={'axis': {'range': [15, 40]}, 'bar': {'color': "white"},
                        'steps': [{'range': [15, 18.5], 'color': "#3498db"}, {'range': [18.5, 25], 'color': "#2ecc71"}, {'range': [25, 30], 'color': "#f1c40f"}, {'range': [30, 40], 'color': "#e74c3c"}]}))
                fig_bmi.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_bmi, use_container_width=True, config={'staticPlot': True})

            # --- EMOJI SPIEGEL ---
            st.markdown("---")
            st.subheader("📐 Körpermaße-Spiegel & Quartalstrend")
            
            col_sil, col_trends = st.columns([0.45, 0.55])
            
            with col_sil:
                svg_html_code = f"""
                <div style="width: 100%; max-width: 550px; margin: 0 auto; background-color: transparent;">
                    <svg viewBox="0 0 520 440" width="100%" height="440" style="background: transparent; overflow: visible;">
                        <defs>
                            <marker id="arrow-yellow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                <path d="M 0 1 L 10 5 L 0 9 z" fill="#f1c40f"/>
                            </marker>
                            <marker id="arrow-blue" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                <path d="M 0 1 L 10 5 L 0 9 z" fill="#3498db"/>
                            </marker>
                            <marker id="arrow-red" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                <path d="M 0 1 L 10 5 L 0 9 z" fill="#e74c3c"/>
                            </marker>
                            <marker id="arrow-green" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                <path d="M 0 1 L 10 5 L 0 9 z" fill="#2ecc71"/>
                            </marker>
                        </defs>

                        <text x="260" y="340" font-size="320" text-anchor="middle" style="filter: drop-shadow(0px 5px 15px rgba(0,0,0,0.65));">🧍‍♂️</text>

                        <foreignObject x="0" y="85" width="160" height="85">
                            <div style='background-color: #1A1A1A; padding: 12px; border-radius: 10px; border-left: 5px solid #f1c40f; box-shadow: 2px 2px 8px rgba(0,0,0,0.5); font-family: sans-serif; color: white;'>
                                <span style='font-size: 12px; color: #aaa; font-weight: bold;'>🦒 Halsumfang</span><br>
                                <b style='font-size: 19px;'>{fmt_dec(latest['Hals'])} cm</b>
                            </div>
                        </foreignObject>
                        <line x1="165" y1="120" x2="235" y2="150" stroke="#f1c40f" stroke-width="2.5" marker-end="url(#arrow-yellow)" />

                        <foreignObject x="-10" y="220" width="160" height="85">
                            <div style='background-color: #1A1A1A; padding: 12px; border-radius: 10px; border-left: 5px solid #e74c3c; box-shadow: 2px 2px 8px rgba(0,0,0,0.5); font-family: sans-serif; color: white;'>
                                <span style='font-size: 12px; color: #aaa; font-weight: bold;'>🍕 Bauchumfang</span><br>
                                <b style='font-size: 19px;'>{fmt_dec(latest['Bauch'])} cm</b>
                            </div>
                        </foreignObject>
                        <line x1="155" y1="250" x2="260" y2="230" stroke="#e74c3c" stroke-width="2.5" marker-end="url(#arrow-red)" />

                        <foreignObject x="360" y="115" width="160" height="85">
                            <div style='background-color: #1A1A1A; padding: 12px; border-radius: 10px; border-left: 5px solid #3498db; box-shadow: 2px 2px 8px rgba(0,0,0,0.5); font-family: sans-serif; color: white;'>
                                <span style='font-size: 12px; color: #aaa; font-weight: bold;'>🦍 Brustumfang</span><br>
                                <b style='font-size: 19px;'>{fmt_dec(latest['Brust'])} cm</b>
                            </div>
                        </foreignObject>
                        <line x1="350" y1="145" x2="260" y2="185" stroke="#3498db" stroke-width="2.5" marker-end="url(#arrow-blue)" />

                        <foreignObject x="360" y="285" width="160" height="85">
                            <div style='background-color: #1A1A1A; padding: 12px; border-radius: 10px; border-left: 5px solid #2ecc71; box-shadow: 2px 2px 8px rgba(0,0,0,0.5); font-family: sans-serif; color: white;'>
                                <span style='font-size: 12px; color: #aaa; font-weight: bold;'>🍗 Oberschenkel</span><br>
                                <b style='font-size: 19px;'>{fmt_dec(latest['Oberschenkel'])} cm</b>
                            </div>
                        </foreignObject>
                        <line x1="355" y1="315" x2="290" y2="310" stroke="#2ecc71" stroke-width="2.5" marker-end="url(#arrow-green)" />
                    </svg>
                </div>
                """
                st.components.v1.html(svg_html_code, height=440, scrolling=False)
                
            with col_trends:
                quartal_ago = pd.Timestamp.now() - pd.Timedelta(days=90)
                df_q = df_daily[df_daily['Datum'] >= quartal_ago].copy()
                if df_q.empty: df_q = df_daily.copy()
                
                if not df_q.empty:
                    df_q = df_q.sort_values('Datum').set_index('Datum')
                    df_biweekly = df_q.resample('14D').last().dropna(subset=['Hals', 'Brust', 'Bauch', 'Oberschenkel']).reset_index()
                    
                    m_labels = [
                        ("Halsumfang 🦒", "Hals", "#f1c40f"), 
                        ("Brustumfang 🦍", "Brust", "#3498db"), 
                        ("Bauchumfang 🍕", "Bauch", "#e74c3c"), 
                        ("Oberschenkel 🍗", "Oberschenkel", "#2ecc71")
                    ]
                    
                    for label, col_key, curve_color in m_labels:
                        fig_mini = go.Figure(go.Scatter(
                            x=df_biweekly['Datum'], y=df_biweekly[col_key], 
                            mode='lines+markers', 
                            line=dict(color=curve_color, width=3),
                            marker=dict(size=6, symbol='circle')
                        ))
                        fig_mini.update_layout(
                            height=105, 
                            margin=dict(l=10, r=10, t=22, b=10), 
                            title=dict(text=f"<b>{label}</b> (14-Tage Intervall / Quartal)", font=dict(size=12, color='#ECEFF1')), 
                            xaxis=dict(showgrid=False, tickformat="%d.%m", tickfont=dict(size=9)), 
                            yaxis=dict(showgrid=True, tickfont=dict(size=9), nticks=4)
                        )
                        st.plotly_chart(fig_mini, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Noch keine Messdaten für das Quartals-Diagramm vorhanden.")

        else:
            st.info("💡 Willkommen! Sobald du Daten in der linken Seitenleiste einträgst, erscheinen hier deine Kurven.")

    with tab2:
        st.header("🔥 Plateau-Breaker & Refeed-Coach")
        
        m_kcal = int(settings.get("maintenance_kcal", 2300))
        
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("Erhaltungsbedarf (100%)", f"{m_kcal} kcal")
        c_m2.metric("Aktuelles Ziel-Limit", f"{limit_kcal} kcal")
        c_m3.metric("Zielgewicht", f"{settings['target_weight']} kg")
        
        st.markdown("---")
        
        st.subheader("🎯 Strategie-Auswahl für die Ziel-Gerade (85 kg)")
        col_strat1, col_strat2 = st.columns(2)
        with col_strat1:
            st.markdown("#### 🌱 Option A: Moderates Defizit")
            st.write(f"• **Ziel:** {m_kcal - 300} kcal / Tag (-300 kcal)")
            st.write("• **Tempo:** Sanfte Abnahme (~0,25 kg/Woche)")
            if st.button("Option A aktivieren (-300 kcal)"):
                settings["custom_target_kcal"] = str(m_kcal - 300)
                settings["deficit_mode"] = "Moderate"
                save_settings_to_db(settings)
                st.success("Moderates Defizit aktiviert! ✅")
                st.rerun()

        with col_strat2:
            st.markdown("#### ⚡ Option B: Zügiges Defizit")
            st.write(f"• **Ziel:** {m_kcal - 500} kcal / Tag (-500 kcal)")
            st.write("• **Tempo:** Schnelle Abnahme (~0,5 kg/Woche)")
            if st.button("Option B aktivieren (-500 kcal)"):
                settings["custom_target_kcal"] = str(m_kcal - 500)
                settings["deficit_mode"] = "Fast"
                save_settings_to_db(settings)
                st.success("Zügiges Defizit aktiviert! 🚀")
                st.rerun()

        st.markdown("---")
        
        st.subheader("🍽️ Dein 3-Tage-Refeed Menüplan auf Erhaltungsniveau")
        plan_data, shop_list = get_refeed_plan(m_kcal)
        t1, t2, t3, t_shop = st.tabs(["Tag 1 Plan", "Tag 2 Plan", "Tag 3 Plan", "🛒 Einkaufsliste"])
        
        for idx, (t_name, tab_obj) in enumerate(zip(["Tag 1", "Tag 2", "Tag 3"], [t1, t2, t3])):
            with tab_obj:
                for item in plan_data[t_name]:
                    st.markdown(f"**{item['Mahlzeit']}** ({item['Kcal']} kcal)")
                    st.markdown(f"👉 *{item['Name']}*")
                    st.caption(item['Details'])
                    st.write("")
                    
        with t_shop:
            st.markdown("#### Zutaten für die 3 Tage Refeed-Phase:")
            for item in shop_list:
                st.checkbox(item, key=f"shop_{item}")

    with tab3:
        st.header("📊 Langzeit-Statistik")
        if not df_filled.empty:
            now = pd.Timestamp.now()
            heute_date = date.today()
            start_der_woche = heute_date - timedelta(days=heute_date.weekday())
            df_this_week = df_daily[df_daily['Datum'].dt.date >= start_der_woche].sort_values('Datum')
            
            periods = {
                "Letzte Woche (Rollen-Basis 7 Tage)": 7, 
                "Letzter Monat": 30, 
                "Letztes Quartal": 90, 
                "Letztes Jahr": 365
            }
            
            st.subheader(f"📅 Aktuelle Kalenderwoche (Seit Mo, {start_der_woche.strftime('%d.%m.%Y')})")
            if not df_this_week.empty:
                c1, c2, c3, c4 = st.columns([1,1,1,1.5])
                w_schritte = df_this_week['Schritte'].sum()
                w_km = w_schritte / 1400
                c1.metric("👣 Schritte", fmt_int(w_schritte), f"🏃‍♂️ {fmt_dec(w_km)} km")
                
                w_diff = df_this_week.iloc[-1]['Gewicht'] - df_this_week.iloc[0]['Gewicht']
                c2.metric("⚖️ Gewicht", f"{fmt_dec(df_this_week.iloc[-1]['Gewicht'])} kg", f"{fmt_dec(w_diff)} kg", delta_color="inverse")
                c3.metric("🔥 Kalorien Out", fmt_int(df_this_week['Kalorien_Out'].sum()))
            st.markdown("---")

    with tab4:
        st.header("📋 Datentabelle & Verwaltung")
        if not df.empty:
            disp_view = df.sort_values(['Datum', 'Uhrzeit'], ascending=False).copy()
            disp_view['Datum'] = disp_view['Datum'].dt.strftime('%d.%m.%Y')
            st.dataframe(disp_view, use_container_width=True, hide_index=True)
