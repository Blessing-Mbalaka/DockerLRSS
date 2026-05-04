from django.contrib import admin
from .models import CustomUser
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Qualification


#Custom User------
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active']
    ordering = ['-created_at']
    search_fields = ['email', 'first_name', 'last_name']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'qualification', 'activated_at', 'deactivated_at')}),
    )

admin.site.register(Qualification)

from .models import PdfAnnotation, GradeChangeLog

@admin.register(PdfAnnotation)
class PdfAnnotationAdmin(admin.ModelAdmin):
    list_display  = ('created_by', 'ann_type', 'submission', 'page', 'role', 'created_at')
    list_filter   = ('ann_type', 'role', 'created_at')
    search_fields = ('created_by__email', 'submission__student_number', 'text')
    readonly_fields = ('created_at', 'updated_at', 'colour')

@admin.register(GradeChangeLog)
class GradeChangeLogAdmin(admin.ModelAdmin):
    list_display  = ('submission', 'tier', 'changed_by', 'changed_at')
    list_filter   = ('tier', 'changed_at')
    search_fields = ('submission__student_number', 'changed_by__email', 'note')
    readonly_fields = ('changed_at',)
