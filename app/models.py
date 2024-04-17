from django.db import models
from django.contrib.auth.models import AbstractUser


class City(models.Model):
    name = models.CharField(max_length=255, unique=True)


class User(AbstractUser):
    phone = models.CharField(max_length=30, unique=True)


class Category(models.Model):

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    name = models.CharField(max_length=255, unique=True)
    parent = models.ForeignKey('self', related_name='children', on_delete=models.CASCADE, blank=True, null=True)
    image = models.ImageField(upload_to='images/%Y/%m/%d', default='default_image.png')

    def __str__(self):
        return f'{self.name}'

    def get_descendants(self):
        descendants = []
        children = self.children.all()
        for child in children:
            descendants.append(child)
            descendants += child.get_descendants()
        return descendants


class Product(models.Model):

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    class Status(models.TextChoices):
        ACTIVE = 'AC', 'Активен'
        ARCHIVED = 'AR', 'В архиве'
        ON_MODERATE = 'MD', 'На модерации'
        CANCELED = 'CN', 'Отклонен'

    class PriceSuffix(models.TextChoices):
        NONE = 'N', 'руб'
        SERVICE = 'S', 'за услугу'
        HOUR = 'H', 'за час'
        UNIT = 'U', 'за единицу'
        DAY = 'D', 'за день'
        MONTH = 'MT', 'за месяц'
        M2 = 'M2', 'за м2'
        M = 'M', 'за м'

    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.IntegerField()
    price_suffix = models.CharField(max_length=3, choices=PriceSuffix.choices, default=PriceSuffix.NONE)
    is_lower_bound = models.BooleanField(default=False)
    status = models.CharField(max_length=2, choices=Status.choices, default=Status.ON_MODERATE)
    author = models.ForeignKey(User, related_name='products', on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    city = models.ForeignKey(City, related_name='products', on_delete=models.CASCADE, null=True)


class ProductFeature(models.Model):
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    product = models.ForeignKey(Product, related_name='features', on_delete=models.CASCADE)


class ProductImage(models.Model):
    image = models.ImageField(upload_to='images/%Y/%m/%d', default='default_image.png')
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    description = models.TextField(blank=True, default='')


class CategoryImage(models.Model):
    image = models.ImageField(upload_to='images/%Y/%m/%d', default='default_image.png')
    category = models.ForeignKey(Category, related_name='images', on_delete=models.CASCADE)
    description = models.TextField(blank=True, default='')


class ProductFavorite(models.Model):
    user = models.ForeignKey(User, related_name='favorites', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='subscribers', on_delete=models.CASCADE)
