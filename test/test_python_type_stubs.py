from __future__ import absolute_import, division, print_function, unicode_literals

import textwrap

MYPY = False
if MYPY:
    import typing  # noqa: F401 # pylint: disable=import-error,unused-import,useless-suppression

import unittest
try:
    # Works for Py 3.3+
    from unittest.mock import Mock
except ImportError:
    # See https://github.com/python/mypy/issues/1153#issuecomment-253842414
    from mock import Mock  # type: ignore

from stone.ir import (
    Alias,
    Api,
    ApiNamespace,
    Boolean,
    List,
    Map,
    Nullable,
    String,
    Struct,
    StructField,
    Timestamp,
    UInt64,
    Union,
    UnionField,
    Void,
    Float64)
from stone.ir.api import ApiRoute
from stone.backends.python_type_stubs import PythonTypeStubsBackend
from test.backend_test_util import _mock_emit

ISO_8601_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

def _make_backend():
    # type: () -> PythonTypeStubsBackend
    return PythonTypeStubsBackend(
        target_folder_path=Mock(),
        args=Mock()
    )

def _make_namespace_with_alias():
    # type: (...) -> ApiNamespace
    ns = ApiNamespace('ns_with_alias')

    struct1 = Struct(name='Struct1', namespace=ns, ast_node=None)
    struct1.set_attributes(None, [StructField('f1', Boolean(), None, None)])
    ns.add_data_type(struct1)

    alias = Alias(name='AliasToStruct1', namespace=ns, ast_node=None)
    alias.set_attributes(doc=None, data_type=struct1)
    ns.add_alias(alias)

    str_type = String(min_length=3)
    str_alias = Alias(name='NotUserDefinedAlias', namespace=ns, ast_node=None)
    str_alias.set_attributes(doc=None, data_type=str_type)
    ns.add_alias(str_alias)

    return ns

def _make_namespace_with_many_structs():
    # type: (...) -> ApiNamespace
    ns = ApiNamespace('ns_with_many_structs')

    struct1 = Struct(name='Struct1', namespace=ns, ast_node=None)
    struct1.set_attributes(None, [StructField('f1', Boolean(), None, None)])
    ns.add_data_type(struct1)

    struct2 = Struct(name='Struct2', namespace=ns, ast_node=None)
    struct2.set_attributes(
        doc=None,
        fields=[
            StructField('f2', List(UInt64()), None, None),
            StructField('f3', Timestamp(ISO_8601_FORMAT), None, None),
            StructField('f4', Map(String(), UInt64()), None, None)
        ]
    )
    ns.add_data_type(struct2)

    return ns

def _make_namespace_with_nested_types():
    # type: (...) -> ApiNamespace
    ns = ApiNamespace('ns_w_nested_types')

    struct = Struct(name='NestedTypes', namespace=ns, ast_node=None)
    struct.set_attributes(
        doc=None,
        fields=[
            StructField(
                name='NullableList',
                data_type=Nullable(
                    List(UInt64())
                ),
                doc=None,
                ast_node=None,
            ),
            StructField(
                name='ListOfNullables',
                data_type=List(
                    Nullable(UInt64())
                ),
                doc=None,
                ast_node=None,
            )
        ]
    )
    ns.add_data_type(struct)

    return ns

def _make_namespace_with_a_union():
    # type: (...) -> ApiNamespace
    ns = ApiNamespace('ns_with_a_union')

    u1 = Union(name='Union', namespace=ns, ast_node=None, closed=True)
    u1.set_attributes(
        doc=None,
        fields=[
            UnionField(
                name="first",
                doc=None,
                data_type=Void(),
                ast_node=None
            ),
            UnionField(
                name="last",
                doc=None,
                data_type=Void(),
                ast_node=None
            ),
        ],
    )
    ns.add_data_type(u1)

    # A more interesting case with non-void variants.
    shape_union = Union(name='Shape', namespace=ns, ast_node=None, closed=True)
    shape_union.set_attributes(
        doc=None,
        fields=[
            UnionField(
                name="point",
                doc=None,
                data_type=Void(),
                ast_node=None
            ),
            UnionField(
                name="circle",
                doc=None,
                data_type=Float64(),
                ast_node=None
            ),
        ],
    )
    ns.add_data_type(shape_union)

    return ns

def _make_namespace_with_empty_union():
    # type: (...) -> ApiNamespace
    ns = ApiNamespace('ns_with_empty_union')

    union = Union(name='EmptyUnion', namespace=ns, ast_node=None, closed=True)
    union.set_attributes(
        doc=None,
        fields=[],
    )
    ns.add_data_type(union)

    return ns

def _make_namespace_with_route():
    # type: (...) -> ApiNamespace
    ns = ApiNamespace("_make_namespace_with_route()")
    mock_ast_node = Mock()
    route_one = ApiRoute(
        name="route_one",
        version=1,
        ast_node=mock_ast_node,
    )
    route_two = ApiRoute(
        name="route_one",
        version=2,
        ast_node=mock_ast_node,
    )
    ns.add_route(route_one)
    ns.add_route(route_two)
    return ns

def _make_namespace_with_route_name_conflict():
    # type: (...) -> ApiNamespace
    ns = ApiNamespace("_make_namespace_with_route()")
    mock_ast_node = Mock()
    route_one = ApiRoute(
        name="route_one_v2",
        version=1,
        ast_node=mock_ast_node,
    )
    route_two = ApiRoute(
        name="route_one",
        version=2,
        ast_node=mock_ast_node,
    )
    ns.add_route(route_one)
    ns.add_route(route_two)
    return ns

def _api():
    api = Api(version="1.0")
    return api

_headers = """\
# -*- coding: utf-8 -*-
# Auto-generated by Stone, do not modify.
# @generated
# flake8: noqa
# pylint: skip-file
try:
    from . import stone_validators as bv
    from . import stone_base as bb
except (ImportError, SystemError, ValueError):
    # Catch errors raised when importing a relative module when not in a package.
    # This makes testing this file directly (outside of a package) easier.
    import stone_validators as bv  # type: ignore
    import stone_base as bb  # type: ignore"""

class TestPythonTypeStubs(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestPythonTypeStubs, self).__init__(*args, **kwargs)
        self.maxDiff = 1000000  # Increase text diff size

    def _evaluate_namespace(self, ns):
        # type: (ApiNamespace) -> typing.Text
        backend = _make_backend()
        emitted = _mock_emit(backend)
        backend._generate_base_namespace_module(ns)

        result = "".join(emitted)
        return result

    def test__generate_base_namespace_module__with_many_structs(self):
        # type: () -> None
        ns = _make_namespace_with_many_structs()
        result = self._evaluate_namespace(ns)
        expected = textwrap.dedent("""\
            {headers}

            class Struct1(object):
                def __init__(self,
                             f1: bool = ...) -> None: ...

                @property
                def f1(self) -> bool: ...

                @f1.setter
                def f1(self, val: bool) -> None: ...

                @f1.deleter
                def f1(self) -> None: ...

            Struct1_validator: bv.Validator = ...

            class Struct2(object):
                def __init__(self,
                             f2: List[long] = ...,
                             f3: datetime.datetime = ...,
                             f4: Dict[Text, long] = ...) -> None: ...

                @property
                def f2(self) -> List[long]: ...

                @f2.setter
                def f2(self, val: List[long]) -> None: ...

                @f2.deleter
                def f2(self) -> None: ...


                @property
                def f3(self) -> datetime.datetime: ...

                @f3.setter
                def f3(self, val: datetime.datetime) -> None: ...

                @f3.deleter
                def f3(self) -> None: ...


                @property
                def f4(self) -> Dict[Text, long]: ...

                @f4.setter
                def f4(self, val: Dict[Text, long]) -> None: ...

                @f4.deleter
                def f4(self) -> None: ...

            Struct2_validator: bv.Validator = ...


            from typing import (
                Dict,
                List,
                Text,
            )

            import datetime
            """).format(headers=_headers)
        self.assertEqual(result, expected)

    def test__generate_base_namespace_module__with_nested_types(self):
        # type: () -> None
        ns = _make_namespace_with_nested_types()
        result = self._evaluate_namespace(ns)
        expected = textwrap.dedent("""\
            {headers}

            class NestedTypes(object):
                def __init__(self,
                             list_of_nullables: List[Optional[long]] = ...,
                             nullable_list: Optional[List[long]] = ...) -> None: ...

                @property
                def list_of_nullables(self) -> List[Optional[long]]: ...

                @list_of_nullables.setter
                def list_of_nullables(self, val: List[Optional[long]]) -> None: ...

                @list_of_nullables.deleter
                def list_of_nullables(self) -> None: ...


                @property
                def nullable_list(self) -> Optional[List[long]]: ...

                @nullable_list.setter
                def nullable_list(self, val: Optional[List[long]]) -> None: ...

                @nullable_list.deleter
                def nullable_list(self) -> None: ...

            NestedTypes_validator: bv.Validator = ...


            from typing import (
                List,
                Optional,
            )
            """).format(headers=_headers)
        self.assertEqual(result, expected)

    def test__generate_base_namespace_module_with_union__generates_stuff(self):
        # type: () -> None
        ns = _make_namespace_with_a_union()
        result = self._evaluate_namespace(ns)
        expected = textwrap.dedent("""\
            {headers}

            class Union(bb.Union):
                first = ...  # type: Union
                last = ...  # type: Union

                def is_first(self) -> bool: ...

                def is_last(self) -> bool: ...

            Union_validator: bv.Validator = ...

            class Shape(bb.Union):
                point = ...  # type: Shape

                def is_point(self) -> bool: ...

                def is_circle(self) -> bool: ...

                @classmethod
                def circle(cls, val: float) -> Shape: ...

                def get_circle(self) -> float: ...

            Shape_validator: bv.Validator = ...

            """).format(headers=_headers)
        self.assertEqual(result, expected)

    def test__generate_base_namespace_module_with_empty_union__generates_pass(self):
        # type: () -> None
        ns = _make_namespace_with_empty_union()
        result = self._evaluate_namespace(ns)
        expected = textwrap.dedent("""\
            {headers}

            class EmptyUnion(bb.Union):
                pass

            EmptyUnion_validator: bv.Validator = ...

            """).format(headers=_headers)
        self.assertEqual(result, expected)

    def test__generate_routes(self):
        # type: () -> None
        ns = _make_namespace_with_route()
        result = self._evaluate_namespace(ns)
        expected = textwrap.dedent("""\
            {headers}

            route_one: bb.Route = ...
            route_one_v2: bb.Route = ...

            """).format(headers=_headers)
        self.assertEqual(result, expected)

    def test__generate_routes_name_conflict(self):
        # type: () -> None
        ns = _make_namespace_with_route_name_conflict()

        with self.assertRaises(RuntimeError) as cm:
            self._evaluate_namespace(ns)
        self.assertEqual(
            'There is a name conflict between {!r} and {!r}'.format(ns.routes[0], ns.routes[1]),
            str(cm.exception))

    def test__generate_base_namespace_module__with_alias(self):
        # type: () -> None
        ns = _make_namespace_with_alias()
        result = self._evaluate_namespace(ns)
        expected = textwrap.dedent("""\
            {headers}

            class Struct1(object):
                def __init__(self,
                             f1: bool = ...) -> None: ...

                @property
                def f1(self) -> bool: ...

                @f1.setter
                def f1(self, val: bool) -> None: ...

                @f1.deleter
                def f1(self) -> None: ...

            Struct1_validator: bv.Validator = ...

            AliasToStruct1_validator: bv.Validator = ...
            AliasToStruct1 = Struct1
            NotUserDefinedAlias_validator: bv.Validator = ...
            """).format(headers=_headers)
        self.assertEqual(result, expected)
