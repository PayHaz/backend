
from rest_framework import generics, status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.permissions import AllowAny
from django.db.models import Max, Min
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import generics
from rest_framework.parsers import FileUploadParser, MultiPartParser
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


from .models import Category, Product, User, City, ProductImage, ProductFavorite
from .serializers import CategoryHierarchySerializer, CategorySerializer, ProductSerializer, UserCreateSerializer, \
    UserSerializer, CitySerializer, ProductCreateSerializer, ProductImageSerializer, UserUpdateSerializer


@api_view(['GET'])
def get_category_tree(request):
    category_id = request.query_params.get('category')
    if category_id:
        try:
            category = Category.objects.get(id=category_id)
            child_categories = category.get_descendants()
            child_categories.append(category)
            return Response(CategoryHierarchySerializer(child_categories, many=True).data)
        except Category.DoesNotExist:
            return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        parent_categories = Category.objects.filter(parent_id=None)
        return Response(CategoryHierarchySerializer(parent_categories, many=True).data)


@api_view(['GET'])
def get_category_list(request):
    parent_categories = Category.objects.filter(parent_id=None)
    return Response(CategorySerializer(parent_categories, many=True).data)


@api_view(['GET'])
def get_city_list(request):
    cities = City.objects.all()
    return Response(CitySerializer(cities, many=True).data)


class ProductList(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductCreateSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def list(self, request, **kwargs):
        queryset = self.get_queryset()
        own = self.request.query_params.get('own', False)

        # проверяем наличие jwt токена
        if request.user.is_authenticated and own:
            # получаем пользователя из токена
            user = request.user
            queryset = queryset.filter(author=user)
        else:
            # если пользователь не аутентифицирован, то фильтруем по x-city-id
            if 'city' in self.request.query_params:
                queryset = queryset.filter(city_id=int(self.request.query_params['city']))
            else:
                # если x-city-id не передан, то выводим все продукты со статусом active
                queryset = queryset.filter(status='AC')

        # получаем значение параметра status из URL
        status = request.query_params.get('status', 'ACTIVE')

        # фильтруем по статусу
        queryset = queryset.filter(status=status).order_by('-created_at')[:20]
        serializer = ProductSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def perform_create(self, serializer):
        author = self.request.user
        serializer.save(author=author)


class ProductSearchView(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        search_name = self.request.query_params.get('name')
        search_city = self.request.query_params.get('city')
        search_category = self.request.query_params.get('category')
        min_price = self.request.query_params.get('minRange')
        max_price = self.request.query_params.get('maxRange')

        queryset = Product.objects.filter(status='AC')

        if search_category:
            # Получаем все дочерние категории
            category_ids = [int(search_category)]
            category_ids += self.get_child_categories(int(search_category))

            queryset = queryset.filter(category_id__in=category_ids)

        if search_name:
            queryset = queryset.filter(name__icontains=search_name)

        if search_city:
            queryset = queryset.filter(city_id=search_city)

        if min_price and max_price:
            queryset = queryset.filter(price__range=(min_price, max_price))

        # Вычисляем минимальную и максимальную стоимость только для отфильтрованных продуктов
        min_price_filtered = queryset.aggregate(Min('price'))['price__min']
        max_price_filtered = queryset.aggregate(Max('price'))['price__max']

        # Добавляем значения минимальной и максимальной стоимости в контекст для использования в сериализаторе
        self.kwargs['min_price'] = min_price_filtered
        self.kwargs['max_price'] = max_price_filtered

        return queryset

    def get_child_categories(self, category_id):
        # Рекурсивная функция для получения всех дочерних категорий
        category_ids = []
        children = Category.objects.filter(parent_id=category_id)
        for child in children:
            category_ids.append(child.id)
            category_ids += self.get_child_categories(child.id)
        return category_ids

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['min_price'] = self.kwargs.get('min_price')
        context['max_price'] = self.kwargs.get('max_price')
        return context

    def get_child_categories(self, category_id):
        # Рекурсивная функция для получения всех дочерних категорий
        category_ids = []
        children = Category.objects.filter(parent_id=category_id)
        for child in children:
            category_ids.append(child.id)
            category_ids += self.get_child_categories(child.id)
        return category_ids


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return obj.author == request.user


class ProductDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if not request.auth:
            serializer = self.get_serializer(instance)
            return Response(serializer.data)

        if instance.author != request.user:
            return Response("Вы не являетесь автором этого продукта", status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        instance.delete()

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()

        if not request.user.is_authenticated:
            return Response("Вы не являетесь автором этого продукта", status=status.HTTP_401_UNAUTHORIZED)

        if instance.author != request.user:
            return Response("Вы не являетесь автором этого продукта", status=status.HTTP_403_FORBIDDEN)

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, *args, **kwargs):
        instance = self.get_object()

        if not request.user.is_authenticated:
            return self.retrieve(request, *args, **kwargs)

        if instance.author != request.user:
            return Response("Вы не являетесь автором этого продукта")

        status = request.data.get('status',
                                  instance.status)
        city_id = request.data.get('city_id', instance.city_id)

        price_suffix = request.data.get('price_suffix', instance.price_suffix)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(status=status, city_id=city_id, price_suffix=price_suffix)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()

        if not request.user.is_authenticated:
            return self.retrieve(request, *args, **kwargs)

        if instance.author != request.user:
            return Response("Вы не являетесь автором этого продукта", status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)



@api_view(['POST'])
@parser_classes([MultiPartParser, FileUploadParser])
@permission_classes([IsAuthenticated])
def upload_product_images(request, product_id):
    serializer = ProductImageSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        product = Product.objects.get(id=product_id)
        if product.author != request.user:
            raise PermissionDenied("You are not the owner of this product")
        serializer.save(product=product)
        return Response(status=201)
    else:
        return Response(serializer.errors, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product_image(request, product_id, image_id):
    try:
        product_image = ProductImage.objects.get(id=image_id, product_id=product_id)
        if product_image.product.author != request.user:
            raise PermissionDenied("You are not the owner of this product")
        product_image.delete()
        return Response(status=204)
    except ProductImage.DoesNotExist:
        return Response(status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_or_delete_favorite(request, product_id):
    if ProductFavorite.objects.filter(user_id=request.user.id, product_id=product_id).exists():
        ProductFavorite.objects.filter(user_id=request.user.id, product_id=product_id).delete()
        return Response(False, status=200)
    else:
        fav = ProductFavorite(user_id=request.user.id, product_id=product_id)
        fav.save()
        return Response(True, status=200)


class UserView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)


class UserCreateAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]


class UserRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = UserUpdateSerializer(instance, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

