from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
import json


REPORTS_FILE = "/var/www/django-projekt/data/berichte.json"
USERS_FILE = "/var/www/django-projekt/data/users.json"
MODULE_FILE = "/var/www/django-projekt/data/module.json"
ROLE_REQUESTS_FILE = "/var/www/django-projekt/data/role_requests.json"


# -------------------------
# kleine Hilfen (nur Session)
# -------------------------
def ctx(request):
    return {
        "username": request.session.get("username"),
        "role": request.session.get("role"),
    }


def vip_or_admin(request):
    return request.session.get("role") in ["vip", "admin"]

# =========================
# EXPORT (mit Klasse)
# =========================

class Exporter:
    def __init__(self, berichte):
        self.berichte = berichte

    def als_json(self):
        return json.dumps(self.berichte, ensure_ascii=False, indent=2)

    def als_csv(self):
        text = "Datum,Modul,Minuten,Beschreibung\n"
        for r in self.berichte:
            datum = str(r.get("datum", ""))
            modul = str(r.get("modul", "")).replace(",", " ")
            minuten = str(r.get("minuten", ""))
            beschreibung = str(r.get("content", "")).replace(",", " ")
            text += f"{datum},{modul},{minuten},{beschreibung}\n"
        return text

    def als_xml(self):
        text = "<berichte>\n"
        for r in self.berichte:
            text += "  <bericht>\n"
            text += "    <datum>" + str(r.get("datum", "")) + "</datum>\n"
            text += "    <modul>" + str(r.get("modul", "")) + "</modul>\n"
            text += "    <minuten>" + str(r.get("minuten", 0)) + "</minuten>\n"
            text += "    <beschreibung>" + str(r.get("content", "")) + "</beschreibung>\n"
            text += "  </bericht>\n"
        text += "</berichte>"
        return text

def export_json(request):
    if not vip_or_admin(request):
        return redirect("uebersicht")

    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            reports = json.load(f)
    except:
        reports = []

    email = request.session.get("email")
    eigene = [r for r in reports if r.get("user") == email]

    exporter = Exporter(eigene)
    data = exporter.als_json()

    response = HttpResponse(data, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="berichte.json"'
    return response


def export_csv(request):
    if not vip_or_admin(request):
        return redirect("uebersicht")

    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            reports = json.load(f)
    except:
        reports = []

    email = request.session.get("email")
    eigene = [r for r in reports if r.get("user") == email]

    exporter = Exporter(eigene)
    data = exporter.als_csv()

    response = HttpResponse(data, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="berichte.csv"'
    return response


def export_xml(request):
    if not vip_or_admin(request):
        return redirect("uebersicht")

    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            reports = json.load(f)
    except:
        reports = []

    email = request.session.get("email")
    eigene = [r for r in reports if r.get("user") == email]

    exporter = Exporter(eigene)
    data = exporter.als_xml()

    response = HttpResponse(data, content_type="application/xml; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="berichte.xml"'
    return response


# -------------------------
# IMPORT (nur JSON)
# -------------------------
def import_json(request):
    if not vip_or_admin(request):
        return redirect("uebersicht")
    if request.method != "POST":
        return redirect("meine_berichte")

    datei = request.FILES.get("datei")
    if not datei or not datei.name.lower().endswith(".json"):
        messages.error(request, "Bitte eine JSON-Datei auswÃ¤hlen.")
        return redirect("meine_berichte")

    email = request.session.get("email")
    username = request.session.get("username")

    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            reports = json.load(f)
    except:
        reports = []

    # alte Berichte vom User entfernen
    reports = [r for r in reports if r.get("user") != email]

    try:
        daten = json.load(datei)  # erwartet Liste
        for b in daten:
            reports.append({
                "id": len(reports) + 1,
                "user": email,
                "username": username,
                "datum": b.get("datum", ""),
                "modul": b.get("modul", ""),
                "minuten": int(b.get("minuten", 0)),
                "content": b.get("content", ""),
            })
    except:
        messages.error(request, "Import fehlgeschlagen.")
        return redirect("meine_berichte")

    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)

    messages.success(request, "Import erfolgreich.")
    return redirect("meine_berichte")


# -------------------------
# LOGIN
# -------------------------

def benutzer_login(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()
        role = request.POST.get("role")

        if not role:
            messages.error(request, "Bitte eine Rolle auswaehlen.")
            return render(request, "login.html")

        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except:
            users = []

        user = None
        for u in users:
            if u.get("email", "").lower() == email:
                user = u
                break

        if not user or user.get("password") != password:
            messages.error(request, "Email oder Passwort ist falsch.")
            return render(request, "login.html")

        if user.get("is_active") is False:
            messages.error(request, "Dein Konto wurde gesperrt.")
            return render(request, "login.html")

        real_role = user.get("role", "simple")

        if real_role == "admin":
            erlaubt = role in ["admin", "vip", "simple"]
        elif real_role == "vip":
            erlaubt = role in ["vip", "simple"]
        else:
            erlaubt = role == "simple"

        if not erlaubt:
            messages.error(request, "Diese Rolle darfst du nicht verwenden.")
            return render(request, "login.html")

        request.session["username"] = user.get("username")
        request.session["email"] = user.get("email")
        request.session["role"] = role

        return redirect("uebersicht")

    return render(request, "login.html")

# -------------------------
# REGISTRIEREN
# -------------------------
def registrieren(request):
    if request.method == "POST":
        fname = (request.POST.get("vorname") or "").strip()
        lname = (request.POST.get("nachname") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        password = (request.POST.get("password") or "").strip()

        if not fname or not lname or not email or not password:
            messages.error(request, "Bitte alle Felder ausfuellen.")
            return render(request, "registrieren.html")

        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except:
            users = []

        for u in users:
            if u.get("email", "").lower() == email:
                messages.error(request, "Email bereits registriert.")
                return render(request, "registrieren.html")

        username = email.split("@")[0]
        users.append({
            "username": username,
            "first_name": fname,
            "last_name": lname,
            "email": email,
            "password": password,
            "role": "simple",
            "is_active": True
        })

        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

        messages.success(request, "Registrierung erfolgreich. Bitte einloggen.")
        return redirect("login")

    return render(request, "registrieren.html")


# -------------------------
# LOGOUT
# -------------------------
def logout_view(request):
    request.session.flush()
    return redirect("login")


# -------------------------
# ueBERSICHT / BERICHTE / MEINE BERICHTE
# -------------------------
def uebersicht(request):
    c = ctx(request)

    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            reports = json.load(f)
    except:
        reports = []

    email = request.session.get("email")
    eigene = [r for r in reports if r.get("user") == email]

    gesamt_minuten = sum(r.get("minuten", 0) for r in eigene)
    c["gesamt_minuten"] = gesamt_minuten
    c["gesamt_stunden"] = round(gesamt_minuten / 60, 2)

    # Minuten pro Modul
    module_map = {}
    for r in eigene:
        m = r.get("modul", "Unbekannt")
        module_map[m] = module_map.get(m, 0) + r.get("minuten", 0)

    module_details = []
    for m, mins in module_map.items():
        module_details.append({
            "name": m,
            "minuten": mins,
            "stunden": round(mins / 60, 2)
        })
    c["module_details"] = module_details

    return render(request, "uebersicht.html", c)


def berichte(request):
    c = ctx(request)

    try:
        with open(MODULE_FILE, "r", encoding="utf-8") as f:
            modules = json.load(f)
    except:
        modules = ["SA"]
        with open(MODULE_FILE, "w", encoding="utf-8") as f:
            json.dump(modules, f, ensure_ascii=False, indent=2)

    c["modules"] = modules

    if request.method == "POST":
        try:
            with open(REPORTS_FILE, "r", encoding="utf-8") as f:
                reports = json.load(f)
        except:
            reports = []

        reports.append({
            "id": len(reports) + 1,
            "user": request.session.get("email"),
            "username": request.session.get("username"),
            "datum": request.POST.get("datum"),
            "modul": request.POST.get("modul"),
            "minuten": int(request.POST.get("minuten") or 0),
            "content": request.POST.get("content", ""),
        })

        with open(REPORTS_FILE, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)

        return redirect("meine_berichte")

    return render(request, "berichte.html", c)


def meine_berichte(request):
    c = ctx(request)

    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            reports = json.load(f)
    except:
        reports = []

    email = request.session.get("email")
    eigene = [r for r in reports if r.get("user") == email]

    c["berichte"] = eigene
    c["gesamt_minuten"] = sum(r.get("minuten", 0) for r in eigene)

    return render(request, "meine_berichte.html", c)


def bericht_loeschen(request, bericht_id):
    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            reports = json.load(f)
    except:
        reports = []

    email = request.session.get("email")
    reports = [r for r in reports if not (r.get("id") == bericht_id and r.get("user") == email)]

    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)

    return redirect("meine_berichte")




# ======================
# Bericht bearbeiten
# ======================
def bericht_bearbeiten(request, bericht_id):
    # Reports laden
    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            reports = json.load(f)
    except:
        reports = []

    user_email = request.session.get("email")

    # passenden Bericht suchen (nur eigener Bericht)
    bericht = None
    for r in reports:
        if r.get("id") == bericht_id and r.get("user") == user_email:
            bericht = r
            break

    if not bericht:
        return redirect("meine_berichte")

    # Module laden fuer Dropdown
    try:
        with open(MODULE_FILE, "r", encoding="utf-8") as f:
            modules = json.load(f)
    except:
        modules = ["SA"]

    if request.method == "POST":
        bericht["datum"] = request.POST.get("datum")
        bericht["modul"] = request.POST.get("modul")
        bericht["minuten"] = int(request.POST.get("minuten") or 0)
        bericht["content"] = request.POST.get("content", "")

        # speichern
        with open(REPORTS_FILE, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)

        return redirect("meine_berichte")

    return render(request, "berichte.html", {
        **ctx(request),
        "edit": True,
        "bericht": bericht,
        "modules": modules,
    })


# ======================
# Einstellungen (Rollenantrag)
# ======================
def einstellungen(request):
    c = ctx(request)

    # Role-Requests laden
    try:
        with open(ROLE_REQUESTS_FILE, "r", encoding="utf-8") as f:
            reqs = json.load(f)
    except:
        reqs = []

    if request.method == "POST":
        zielrolle = request.POST.get("zielrolle")
        begruendung = request.POST.get("begruendung", "")

        reqs.append({
            "id": len(reqs) + 1,
            "username": request.session.get("username"),
            "email": request.session.get("email"),
            "current_role": request.session.get("role"),
            "requested_role": zielrolle,
            "reason": begruendung,
            "status": "offen",
        })

        with open(ROLE_REQUESTS_FILE, "w", encoding="utf-8") as f:
            json.dump(reqs, f, ensure_ascii=False, indent=2)

        return redirect("einstellungen")

    return render(request, "einstellungen.html", c)


# ======================
# Admin: Rollenantraege ansehen
# ======================
def rollen_antraege(request):
    role = request.session.get("role")
    if role != "admin":
        messages.error(request, "Kein Zugriff. Nur Administratoren duerfen dies sehen.")
        return redirect("uebersicht")

    try:
        with open(ROLE_REQUESTS_FILE, "r", encoding="utf-8") as f:
            role_requests = json.load(f)
    except:
        role_requests = []

    return render(request, "rollen_antraege.html", {
        "username": request.session.get("username"),
        "role": role,
        "role_requests": role_requests,
    })


# ======================
# Admin: Rolle genehmigen
# ======================
def rolle_genehmigen(request, request_id):
    if request.session.get("role") != "admin":
        return redirect("uebersicht")

    # role_requests laden
    try:
        with open(ROLE_REQUESTS_FILE, "r", encoding="utf-8") as f:
            role_requests = json.load(f)
    except:
        role_requests = []

    # users laden
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = []

    req = None
    for r in role_requests:
        if r.get("id") == request_id:
            req = r
            break

    if not req:
        messages.error(request, "Antrag nicht gefunden.")
        return redirect("rollen_antraege")

    # user rolle Ã¤ndern
    for u in users:
        if u.get("email", "").lower() == (req.get("email", "").lower()):
            u["role"] = req.get("requested_role")
            break

    # speichern users
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    # Antrag entfernen
    role_requests = [r for r in role_requests if r.get("id") != request_id]

    with open(ROLE_REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(role_requests, f, ensure_ascii=False, indent=2)

    return redirect("rollen_antraege")


# ======================
# Admin: Rolle ablehnen
# ======================
def rolle_ablehnen(request, request_id):
    if request.session.get("role") != "admin":
        return redirect("uebersicht")

    try:
        with open(ROLE_REQUESTS_FILE, "r", encoding="utf-8") as f:
            role_requests = json.load(f)
    except:
        role_requests = []

    role_requests = [r for r in role_requests if r.get("id") != request_id]

    with open(ROLE_REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(role_requests, f, ensure_ascii=False, indent=2)

    return redirect("rollen_antraege")


# ======================
# Admin: Module verwalten
# ======================
def module_verwalten(request):
    if request.session.get("role") != "admin":
        return redirect("uebersicht")

    try:
        with open(MODULE_FILE, "r", encoding="utf-8") as f:
            modules = json.load(f)
    except:
        modules = ["SA"]

    if request.method == "POST":
        neues_modul = (request.POST.get("modul") or "").strip()
        if neues_modul and neues_modul not in modules:
            modules.append(neues_modul)

            with open(MODULE_FILE, "w", encoding="utf-8") as f:
                json.dump(modules, f, ensure_ascii=False, indent=2)

    return render(request, "module_verwalten.html", {
        **ctx(request),
        "modules": modules,
    })


def modul_loeschen(request, modul_name):
    if request.session.get("role") != "admin":
        return redirect("uebersicht")

    try:
        with open(MODULE_FILE, "r", encoding="utf-8") as f:
            modules = json.load(f)
    except:
        modules = ["SA"]

    if modul_name in modules:
        modules.remove(modul_name)

        with open(MODULE_FILE, "w", encoding="utf-8") as f:
            json.dump(modules, f, ensure_ascii=False, indent=2)

    return redirect("module_verwalten")


# ======================
# Admin: Benutzer verwalten / sperren
# ======================
def benutzer_verwalten(request):
    if request.session.get("role") != "admin":
        return redirect("uebersicht")

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = []

    return render(request, "benutzer_verwalten.html", {
        "username": request.session.get("username"),
        "role": request.session.get("role"),
        "users": users,
    })


def benutzer_sperren(request, email):
    if request.session.get("role") != "admin":
        return redirect("uebersicht")

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = []

    admin_email = request.session.get("email")

    for u in users:
        if u.get("email") == email and u.get("email") != admin_email:
            u["is_active"] = False

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    return redirect("benutzer_verwalten")


def benutzer_entsperren(request, email):
    if request.session.get("role") != "admin":
        return redirect("uebersicht")

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = []

    for u in users:
        if u.get("email") == email:
            u["is_active"] = True

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    return redirect("benutzer_verwalten")

