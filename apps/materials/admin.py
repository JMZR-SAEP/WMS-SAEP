from django.contrib import admin

from .models import GrupoMaterial, SubgrupoMaterial


@admin.register(GrupoMaterial)
class GrupoMaterialAdmin(admin.ModelAdmin):
    list_display = ("codigo_grupo", "nome", "updated_at")
    search_fields = ("codigo_grupo", "nome")
    ordering = ("codigo_grupo",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Informações", {"fields": ("codigo_grupo", "nome")}),
        ("Datas", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(SubgrupoMaterial)
class SubgrupoMaterialAdmin(admin.ModelAdmin):
    list_display = ("grupo", "codigo_subgrupo", "nome", "updated_at")
    list_filter = ("grupo",)
    list_select_related = ("grupo",)
    search_fields = ("codigo_subgrupo", "nome", "grupo__codigo_grupo")
    ordering = ("grupo", "codigo_subgrupo")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Informações", {"fields": ("grupo", "codigo_subgrupo", "nome")}),
        ("Datas", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
