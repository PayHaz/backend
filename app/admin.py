from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Product, ProductImage, ProductFeature, Category, City, ProductFavorite, CategoryImage


class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'price', 'author')


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
