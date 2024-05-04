from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Product, ProductImage, ProductFeature, Category, City, ProductFavorite, CategoryImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # Количество пустых форм для загрузки изображений


class ProductFeatureInline(admin.TabularInline):
    model = ProductFeature
    extra = 1  # Количество пустых форм для характеристик


class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, ProductFeatureInline]
    list_display = ['name', 'description', 'price', 'status', 'author', 'category', 'created_at', 'updated_at', 'city']
    search_fields = ['name', 'description']


class ProductCity(admin.ModelAdmin):
    list_display = ('id', 'name')


admin.site.register(User, UserAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductImage)
admin.site.register(ProductFeature)
admin.site.register(Category)
admin.site.register(City, ProductCity)
admin.site.register(ProductFavorite)
admin.site.register(CategoryImage)
