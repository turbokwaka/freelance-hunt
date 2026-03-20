from django.contrib import admin
from .models import Ad

# Register your models here.
@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = ('title', 'budget', 'employer', 'created_at')
    search_fields = ('title', 'employer', 'description')
    list_filter = ('created_at',)
