from abc import ABC, abstractmethod

from django.db.models import Q

from baserow.contrib.database.fields.field_filters import OptionallyAnnotatedQ
from baserow.contrib.database.fields.field_types import FormulaFieldType
from baserow.contrib.database.fields.filter_support.base import (
    HasNumericValueComparableToFilterSupport,
    HasValueContainsFilterSupport,
    HasValueContainsWordFilterSupport,
    HasValueEmptyFilterSupport,
    HasValueEqualFilterSupport,
    HasValueLengthIsLowerThanFilterSupport,
)
from baserow.contrib.database.fields.registries import field_type_registry
from baserow.contrib.database.formula import (
    BaserowFormulaNumberType,
    BaserowFormulaTextType,
)
from baserow.contrib.database.formula.expression_generator.django_expressions import (
    ComparisonOperator,
)
from baserow.contrib.database.formula.types.formula_types import (
    BaserowFormulaBooleanType,
    BaserowFormulaCharType,
    BaserowFormulaSingleSelectType,
    BaserowFormulaURLType,
)

from .registries import ViewFilterType
from .view_filters import NotViewFilterTypeMixin


class HasEmptyValueViewFilterType(ViewFilterType):
    """
    The filter can be used to check for empty condition for
    items in an array.
    """

    type = "has_empty_value"
    compatible_field_types = [
        FormulaFieldType.compatible_with_formula_types(
            FormulaFieldType.array_of(BaserowFormulaTextType.type),
            FormulaFieldType.array_of(BaserowFormulaCharType.type),
            FormulaFieldType.array_of(BaserowFormulaURLType.type),
            FormulaFieldType.array_of(BaserowFormulaSingleSelectType.type),
            FormulaFieldType.array_of(BaserowFormulaNumberType.type),
        ),
    ]

    def get_filter(self, field_name, value, model_field, field) -> OptionallyAnnotatedQ:
        field_type: HasValueEmptyFilterSupport = field_type_registry.get_by_model(field)
        return field_type.get_in_array_empty_query(field_name, model_field, field)


class HasNotEmptyValueViewFilterType(
    NotViewFilterTypeMixin, HasEmptyValueViewFilterType
):
    type = "has_not_empty_value"


class ComparisonHasValueFilter(ViewFilterType, ABC):
    """
    A filter that can be used to compare the values in an array with a specific value
    using a comparison operator.
    """

    def get_filter(
        self, field_name, value: str, model_field, field
    ) -> OptionallyAnnotatedQ:
        if value == "":
            return Q()

        field_type = field_type_registry.get_by_model(field)
        try:
            filter_value = field_type.prepare_filter_value(field, model_field, value)
        except ValueError:  # invalid filter value for the field
            return self.default_filter_on_exception()

        return self.get_filter_expression(field_name, filter_value, model_field, field)

    @abstractmethod
    def get_filter_expression(
        self, field_name, value, model_field, field
    ) -> OptionallyAnnotatedQ:
        """
        Return the filter expression to use for the required comparison.

        :param field_name: The name of the field to filter on.
        :param value: A non-empty string value to compare against.
        :param model_field: The model field instance.
        :param field: The field instance.
        :return: The filter expression to use.
        :raises ValidationError: If the value cannot be parsed to the proper type.
        """


class HasValueEqualViewFilterType(ComparisonHasValueFilter):
    """
    The filter can be used to check for "is" condition for
    items in an array.
    """

    type = "has_value_equal"
    compatible_field_types = [
        FormulaFieldType.compatible_with_formula_types(
            FormulaFieldType.array_of(BaserowFormulaTextType.type),
            FormulaFieldType.array_of(BaserowFormulaCharType.type),
            FormulaFieldType.array_of(BaserowFormulaURLType.type),
            FormulaFieldType.array_of(BaserowFormulaBooleanType.type),
            FormulaFieldType.array_of(BaserowFormulaSingleSelectType.type),
            FormulaFieldType.array_of(BaserowFormulaNumberType.type),
        ),
    ]

    def get_filter_expression(
        self, field_name, value, model_field, field
    ) -> OptionallyAnnotatedQ:
        field_type: HasValueEqualFilterSupport = field_type_registry.get_by_model(field)
        return field_type.get_in_array_is_query(field_name, value, model_field, field)


class HasNotValueEqualViewFilterType(
    NotViewFilterTypeMixin, HasValueEqualViewFilterType
):
    type = "has_not_value_equal"


class HasValueContainsViewFilterType(ViewFilterType):
    """
    The filter can be used to check for "contains" condition for
    items in an array.
    """

    type = "has_value_contains"
    compatible_field_types = [
        FormulaFieldType.compatible_with_formula_types(
            FormulaFieldType.array_of(BaserowFormulaTextType.type),
            FormulaFieldType.array_of(BaserowFormulaCharType.type),
            FormulaFieldType.array_of(BaserowFormulaURLType.type),
            FormulaFieldType.array_of(BaserowFormulaSingleSelectType.type),
            FormulaFieldType.array_of(BaserowFormulaNumberType.type),
        ),
    ]

    def get_filter(self, field_name, value, model_field, field) -> OptionallyAnnotatedQ:
        if value == "":
            return Q()

        field_type: HasValueContainsFilterSupport = field_type_registry.get_by_model(
            field
        )
        return field_type.get_in_array_contains_query(
            field_name, value, model_field, field
        )


class HasNotValueContainsViewFilterType(
    NotViewFilterTypeMixin, HasValueContainsViewFilterType
):
    type = "has_not_value_contains"


class HasValueContainsWordViewFilterType(ViewFilterType):
    """
    The filter can be used to check for "contains word" condition
    for items in an array.
    """

    type = "has_value_contains_word"
    compatible_field_types = [
        FormulaFieldType.compatible_with_formula_types(
            FormulaFieldType.array_of(BaserowFormulaTextType.type),
            FormulaFieldType.array_of(BaserowFormulaCharType.type),
            FormulaFieldType.array_of(BaserowFormulaURLType.type),
            FormulaFieldType.array_of(BaserowFormulaSingleSelectType.type),
        ),
    ]

    def get_filter(self, field_name, value, model_field, field) -> OptionallyAnnotatedQ:
        if value == "":
            return Q()

        field_type: HasValueContainsWordFilterSupport = (
            field_type_registry.get_by_model(field)
        )
        return field_type.get_in_array_contains_word_query(
            field_name, value, model_field, field
        )


class HasNotValueContainsWordViewFilterType(
    NotViewFilterTypeMixin, HasValueContainsWordViewFilterType
):
    type = "has_not_value_contains_word"


class HasValueLengthIsLowerThanViewFilterType(ViewFilterType):
    """
    The filter can be used to check for "length is lower than" condition
    for items in an array.
    """

    type = "has_value_length_is_lower_than"
    compatible_field_types = [
        FormulaFieldType.compatible_with_formula_types(
            FormulaFieldType.array_of(BaserowFormulaTextType.type),
            FormulaFieldType.array_of(BaserowFormulaCharType.type),
            FormulaFieldType.array_of(BaserowFormulaURLType.type),
        ),
    ]

    def get_filter(self, field_name, value, model_field, field) -> OptionallyAnnotatedQ:
        value = value.strip()
        if value == "":
            return Q()

        try:
            # The value is expected to be an integer representing the length to compare
            filter_value = int(value)
        except (ValueError, TypeError):
            return self.default_filter_on_exception()

        field_type: HasValueLengthIsLowerThanFilterSupport = (
            field_type_registry.get_by_model(field)
        )
        return field_type.get_in_array_length_is_lower_than_query(
            field_name, filter_value, model_field, field
        )


class HasAllValuesEqualViewFilterType(ComparisonHasValueFilter):
    """
    The filter checks if all values in an array are equal to a specific value.
    """

    type = "has_all_values_equal"
    compatible_field_types = [
        FormulaFieldType.compatible_with_formula_types(
            FormulaFieldType.array_of(BaserowFormulaBooleanType.type)
        ),
    ]

    def get_filter_expression(
        self, field_name, value, model_field, field
    ) -> OptionallyAnnotatedQ:
        field_type: HasAllValuesEqualViewFilterType = field_type_registry.get_by_model(
            field
        )
        return field_type.get_has_all_values_equal_query(
            field_name, value, model_field, field
        )


class HasAnySelectOptionEqualViewFilterType(HasValueEqualViewFilterType):
    """
    This filter can be used to verify if any of the select options in an array
    are equal to the option IDs provided.
    """

    type = "has_any_select_option_equal"
    compatible_field_types = [
        FormulaFieldType.compatible_with_formula_types(
            FormulaFieldType.array_of(BaserowFormulaSingleSelectType.type),
        ),
    ]

    def get_filter(self, field_name, value, model_field, field) -> OptionallyAnnotatedQ:
        if value == "":
            return Q()

        return super().get_filter(field_name, value.split(","), model_field, field)


class HasNoneSelectOptionEqualViewFilterType(
    NotViewFilterTypeMixin, HasAnySelectOptionEqualViewFilterType
):
    """
    This filter can be used to verify if none of the select options in an array are
    equal to the option IDs provided
    """

    type = "has_none_select_option_equal"


class hasValueComparableToFilter(ComparisonHasValueFilter):
    type = "has_value_higher"
    compatible_field_types = [
        FormulaFieldType.compatible_with_formula_types(
            FormulaFieldType.array_of(BaserowFormulaNumberType.type)
        ),
    ]

    def get_filter_expression(self, field_name, value, model_field, field):
        field_type: HasNumericValueComparableToFilterSupport = (
            field_type_registry.get_by_model(field)
        )
        return field_type.get_has_numeric_value_comparable_to_filter_query(
            field_name, value, model_field, field, ComparisonOperator.HIGHER_THAN
        )


class HasNotValueHigherThanFilterType(
    NotViewFilterTypeMixin, hasValueComparableToFilter
):
    type = "has_not_value_higher"


class HasValueHigherOrEqualThanFilter(ComparisonHasValueFilter):
    type = "has_value_higher_or_equal"
    compatible_field_types = [
        FormulaFieldType.compatible_with_formula_types(
            FormulaFieldType.array_of(BaserowFormulaNumberType.type)
        ),
    ]

    def get_filter_expression(self, field_name, value, model_field, field):
        field_type: HasNumericValueComparableToFilterSupport = (
            field_type_registry.get_by_model(field)
        )
        return field_type.get_has_numeric_value_comparable_to_filter_query(
            field_name,
            value,
            model_field,
            field,
            ComparisonOperator.HIGHER_THAN_OR_EQUAL,
        )


class HasNotValueHigherOrEqualTHanFilterType(
    NotViewFilterTypeMixin, HasValueHigherOrEqualThanFilter
):
    type = "has_not_value_higher_or_equal"


class HasValueLowerThanFilter(ComparisonHasValueFilter):
    type = "has_value_lower"
    compatible_field_types = [
        FormulaFieldType.compatible_with_formula_types(
            FormulaFieldType.array_of(BaserowFormulaNumberType.type)
        ),
    ]

    def get_filter_expression(self, field_name, value, model_field, field):
        field_type: HasNumericValueComparableToFilterSupport = (
            field_type_registry.get_by_model(field)
        )
        return field_type.get_has_numeric_value_comparable_to_filter_query(
            field_name, value, model_field, field, ComparisonOperator.LOWER_THAN
        )


class HasNotValueLowerThanFilterType(NotViewFilterTypeMixin, HasValueLowerThanFilter):
    type = "has_not_value_lower"


class HasValueLowerOrEqualThanFilter(ComparisonHasValueFilter):
    type = "has_value_lower_or_equal"
    compatible_field_types = [
        FormulaFieldType.compatible_with_formula_types(
            FormulaFieldType.array_of(BaserowFormulaNumberType.type)
        ),
    ]

    def get_filter_expression(self, field_name, value, model_field, field):
        field_type: HasNumericValueComparableToFilterSupport = (
            field_type_registry.get_by_model(field)
        )
        return field_type.get_has_numeric_value_comparable_to_filter_query(
            field_name,
            value,
            model_field,
            field,
            ComparisonOperator.LOWER_THAN_OR_EQUAL,
        )


class HasNotValueLowerOrEqualTHanFilterType(
    NotViewFilterTypeMixin, HasValueLowerOrEqualThanFilter
):
    type = "has_not_value_lower_or_equal"
