from django.contrib import admin
from django.urls import path
from meine_app import views
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth
    path("", views.benutzer_login, name="start"),
    path("login/", views.benutzer_login, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Registrierung
    path("registrieren/", views.registrieren, name="registrieren"),
    # Seiten
    path("uebersicht/", views.uebersicht, name="uebersicht"),
    path("berichte/", views.berichte, name="berichte"),
    path("meine_berichte/", views.meine_berichte, name="meine_berichte"),
    path("einstellungen/", views.einstellungen, name="einstellungen"),
    path("rollenantraege/", views.rollen_antraege, name="rollen_antraege"),
    path("rollen-antraege/genehmigen/<int:request_id>/", views.rolle_genehmigen, name="rolle_genehmigen"),
    path("rollen-antraege/ablehnen/<int:request_id>/", views.rolle_ablehnen, name="rolle_ablehnen"),
    path("berichte/loeschen/<int:bericht_id>/", views.bericht_loeschen, name="bericht_loeschen"),
    path("berichte/bearbeiten/<int:bericht_id>/", views.bericht_bearbeiten, name="bericht_bearbeiten"),
    path("export/json/", views.export_json, name="export_json"),
    path("export/csv/", views.export_csv, name="export_csv"),
    path("export/xml/", views.export_xml, name="export_xml"),
    path("import/", views.import_berichte, name="import_berichte"),
    path("module/", views.module_verwalten, name="module_verwalten"),
    path("module/loeschen/<str:modul_name>/", views.modul_loeschen, name="modul_loeschen"),
    path("benutzer/", views.benutzer_verwalten, name="benutzer_verwalten"),
    path("benutzer/sperren/<str:email>/", views.benutzer_sperren, name="benutzer_sperren"),
    path("benutzer/entsperren/<str:email>/", views.benutzer_entsperren, name="benutzer_entsperren"),
 ]
# >>> Static Files fuer Entwicklungsmodus <<<
if settings.DEBUG:
    from django.conf import settings
from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)