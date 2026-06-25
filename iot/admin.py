"""Administration Django du journal des scans."""
from django.contrib import admin

from .models import JournalScan


@admin.register(JournalScan)
class JournalScanAdmin(admin.ModelAdmin):
    list_display = ("cree_le", "uid", "terminal", "type_scan", "horodatage_carte")
    list_filter = ("type_scan",)
    search_fields = ("uid", "nonce")
    date_hierarchy = "cree_le"
    readonly_fields = ("cree_le",)
