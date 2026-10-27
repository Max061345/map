from rest_framework import serializers
from .models import Category


class CategorySerializers(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'created_at')
        read_only_fields = ('id', 'slug', 'created_at')

    def validate_name(self, value):
        stripped_value = value.strip()
        if not stripped_value:
            raise serializers.ValidationError("Category name cannot be empty or contain only whitespace.")

        query = Category.objects.filter(name__iexact=stripped_value)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError("A category with this name already exists.")

        return stripped_value