from rest_framework import serializers

from .models import Category, Product, User, City, ProductFeature, ProductImage


class CategoryHierarchySerializer(serializers.ModelSerializer):
    value = serializers.IntegerField(source='id')
    title = serializers.CharField(source='name')
    children = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField('get_images')

    class Meta:
        model = Category
        fields = ('value', 'title', 'children', 'image')

    def get_children(self, obj):
        return CategoryHierarchySerializer(obj.children, many=True).data

    def get_images(self, obj):
        return [{'id': image.id, 'img': image.image.url} for image in obj.images.all()]


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ('id', 'name', 'image')



class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ('id', 'name',)


class ProductFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFeature
        fields = ('name', 'value')

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.value = validated_data.get('value', instance.value)
        instance.save()
        return instance


class UserDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone')


class ProductSerializer(serializers.ModelSerializer):
    price_suffix = serializers.CharField(source='get_price_suffix_display')
    city_id = serializers.SerializerMethodField('get_city_id')
    city_name = serializers.SerializerMethodField('get_city_name')
    images = serializers.SerializerMethodField('get_images')

    min_price = serializers.SerializerMethodField()
    max_price = serializers.SerializerMethodField()
    features = ProductFeatureSerializer(many=True)
    is_favorite = serializers.SerializerMethodField('is_favorite_method')
    author = UserDataSerializer()

    class Meta:
        model = Product
        fields = ('id', 'images', 'name', 'description', 'price', 'price_suffix', 'is_lower_bound', 'category', 'city_id', 'city_name', 'min_price', 'max_price', 'features', 'is_favorite', 'author')

    def get_images(self, obj):
        return [{'id': image.id, 'img': image.image.url} for image in obj.images.all()]

    def get_city_id(self, obj: Product):
        return obj.city.id if obj.city else None

    def get_city_name(self, obj: Product):
        return obj.city.name if obj.city else None

    def get_min_price(self, obj):
        min_price_filtered = self.context.get('min_price')
        if min_price_filtered is None:
            # Если значение не передано, то возвращаем минимальную стоимость по умолчанию
            return obj.price
        else:
            return min(obj.price, min_price_filtered)

    def get_max_price(self, obj):
        max_price_filtered = self.context.get('max_price')
        if max_price_filtered is None:
            # Если значение не передано, то возвращаем максимальную стоимость по умолчанию
            return obj.price
        else:
            return max(obj.price, max_price_filtered)

    def is_favorite_method(self, obj):
        user = None
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        if user and user.id in [sub.user.id for sub in obj.subscribers.all()]:
            return True
        return False

    def update(self, instance, validated_data):
        features_data = validated_data.pop('features', [])
        instance.features.all().delete()
        for feature_data in features_data:
            name = feature_data.get('name')
            value = feature_data.get('value')
            ProductFeature.objects.create(product=instance, name=name, value=value)

        for key, value in validated_data.items():
            setattr(instance, key, value)

        instance.save()
        return instance


class UserSerializer(serializers.ModelSerializer):
    favorites = serializers.SerializerMethodField('get_favorites')

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'phone', 'favorites')

    def get_favorites(self, obj):
        return ProductSerializer([fav.product for fav in obj.favorites.all()], many=True, context=self.context).data

    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.save()
        return instance


class ProductCreateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    features = ProductFeatureSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = (
            'id',
            'name',
            'description',
            'price',
            'price_suffix',
            'is_lower_bound',
            'category',
            'city',
            'features'
        )

    def create(self, validated_data):
        features_data = validated_data.pop('features', [])
        product = Product.objects.create(**validated_data)
        for feature in features_data:
            ProductFeature.objects.create(product=product, **feature)
        return product


class ProductImageSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False, use_url=False),
        write_only=True
    )

    class Meta:
        model = ProductImage
        fields = ('id', 'images')

    def create(self, validated_data):
        uploaded_images = validated_data.pop("images")
        product_id = self.context['request'].parser_context['kwargs']['product_id']
        for image in uploaded_images:
            ProductImage.objects.create(product_id=product_id, image=image)
        return uploaded_images


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone')


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name', 'phone')

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone=validated_data['phone'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user