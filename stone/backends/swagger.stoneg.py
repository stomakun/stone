import argparse
import json
import re

from typing import Dict, Text, Union, List, Optional

from stone.backends.helpers import split_words, fmt_pascal
from stone.backends.swagger_rsrc import stone_serializers
from stone.backends.swagger_rsrc.rocks import Rock_validator, Rock, Info as RocksInfo
from stone.ir import Api, ApiNamespace, ApiRoute, DataType, is_primitive_type, is_boolean_type, is_list_type, \
    is_numeric_type, is_string_type, is_void_type, is_timestamp_type, is_nullable_type, is_struct_type, \
    UserDefined, is_union_type, is_user_defined_type, Struct, Union as StoneUnion
from stone.backend import CodeBackend
from stone.backends.swagger_objects import Swagger, Info, Paths, PathItem, Operation, Schema, Reference, \
    Responses, Response, Parameter, Definitions, ParametersDefinitions

SWAGGER_VERSION = '2.0'
SPLIT_DOC_REGEX = re.compile(r'(.*?)\.(?:[^\w\d]|$)(.*)', flags=re.MULTILINE | re.DOTALL)

_cmdline_parser = argparse.ArgumentParser()
_cmdline_parser.add_argument('-r', '--rock', required=True, help='Input rock file.')


def fmt_path(name):
    # type: (Text) -> Text
    parts = [' '.join(
        [word.capitalize() for word in split_words(part) if word.strip()]
    ) for part in name.split('/') if part.strip()]
    return ' - '.join(parts)


class Context(object):

    def __init__(self, rock):
        # type: (Rock) -> None
        self.rock = rock
        self.schemas = {}   # type: Dict[Text, Schema]


class SwaggerBackend(CodeBackend):

    cmdline_parser = _cmdline_parser

    def generate(self, api):
        # type: (Api) -> None
        with open(self.args.rock, 'r') as f:
            rock = stone_serializers.json_decode(Rock_validator, f.read())
        ctx = Context(rock)
        all_paths = Paths({})
        for namespace in rock.namespaces:
            paths = self._generate_paths(ctx, api.namespaces[namespace])
            all_paths.update(paths)
        with self.output_to_relative_path(rock.name):
            swagger = self._generate_swagger(ctx, all_paths)
            self.emit_raw(json.dumps(swagger, default=lambda o: o.dict(), indent=2) + '\n')

    def _generate_swagger(self, ctx, paths):
        # type: (Context, Paths) -> Swagger
        info = self._generate_info(ctx.rock.swagger.info)
        paths = paths
        definitions = self._generate_definitions(ctx)
        consumes = ctx.rock.swagger.consumes
        produces = ctx.rock.swagger.produces
        host = ctx.rock.swagger.host
        base_path = ctx.rock.swagger.base_path
        parameters = self._generate_parameters_object(ctx)
        swagger = Swagger(SWAGGER_VERSION, info, paths, consumes=consumes, produces=produces, definitions=definitions,
                          parameters=parameters, host=host, basePath=base_path)
        return swagger

    def _generate_info(self, info):
        # type: (RocksInfo) -> Info
        info = Info(info.title, info.version, description=info.description)
        return info

    def _generate_parameters_object(self, ctx):
        # type: (Context) -> Optional[ParametersDefinitions]
        if ctx.rock.swagger.parameters is None:
            return None
        parameters = {}  # type: Dict[Text, Parameter]
        for (param_name, param_def) in ctx.rock.swagger.parameters.items():
            parameter = Parameter(name=param_def.name, inParam=param_def.in_param, description=param_def.description,
                                  required=param_def.required, type=param_def.type)
            parameters[param_name] = parameter
        return ParametersDefinitions(parameters)

    def _generate_paths(self, ctx, namespace):
        # type: (Context, ApiNamespace) -> Paths
        paths = {}  # type: Dict[Text, PathItem]
        for route in namespace.routes:
            fq_path = '/' + namespace.name + '/' + route.name
            paths[fq_path] = self._generate_path_item(ctx, route, fq_path)
        return Paths(paths)

    def _generate_path_item(self, ctx, route, fq_path):
        # type: (Context, ApiRoute, Text) -> PathItem
        post = self._generate_operation(ctx, route, fq_path)
        path_item = PathItem(post=post)
        return path_item

    def _generate_operation(self, ctx, route, fq_path):
        # type: (Context, ApiRoute, Text) -> Operation
        summary = fmt_path(fq_path)
        description = route.doc
        parameters = self._generate_parameters(ctx, route, fq_path)
        responses = self._generate_responses(ctx, route)
        operation_id = fmt_pascal(fq_path)
        operation = Operation(responses, summary=summary, description=description, parameters=parameters, operationId=operation_id)
        return operation

    def _generate_parameters(self, ctx, route, fq_path):
        # type: (Context, ApiRoute, Text) -> List[Union[Parameter, Reference]]
        schema = self._generate_for_datatype(ctx, route.arg_data_type)
        parameters = [Parameter('body', 'body', schema=schema)]  # type: List[Union[Parameter, Reference]]
        if ctx.rock.parameters is not None:
            for (pattern, parameter_name) in ctx.rock.parameters.items():
                if re.match(pattern, fq_path):
                    parameters.append(self._generate_reference_for_parameter(parameter_name))
        return parameters

    def _generate_for_datatype(self, ctx, data_type):
        # type: (Context, DataType) -> Union[Schema, Reference]
        if is_primitive_type(data_type):
            schema = self._generate_primitive_type_schema(data_type)
        elif is_nullable_type(data_type):
            schema = self._generate_for_datatype(ctx, data_type.data_type)
        elif is_list_type(data_type):
            schema = Schema(type='array', items=self._generate_for_datatype(ctx, data_type.data_type))
        else:
            assert is_user_defined_type(data_type), "unknown field data_type %s" % data_type
            if data_type.name not in ctx.schemas:
                ctx.schemas[data_type.name] = self._generate_user_defined_schema(ctx, data_type)
            schema = self._generate_reference_for_datatype(data_type)
        return schema

    def _generate_responses(self, ctx, route):
        # type: (Context, ApiRoute) -> Responses
        default_schema = self._generate_for_datatype(ctx, route.error_data_type)
        default_response = Response('Error', schema=default_schema)
        ok_schema = self._generate_for_datatype(ctx, route.result_data_type)
        ok_response = Response('Success', schema=ok_schema)
        status_codes = {'200': ok_response}
        responses = Responses(default=default_response, statusCodes=status_codes)
        return responses

    def _generate_definitions(self, ctx):
        # type: (Context) -> Definitions
        definitions = Definitions(schemas=ctx.schemas)
        return definitions

    def _generate_user_defined_schema(self, ctx, data_type):
        # type: (Context, UserDefined) -> Schema
        if is_struct_type(data_type):
            schema = self._generate_from_struct(ctx, data_type)
        elif is_union_type(data_type):
            schema = self._generate_from_union(ctx, data_type)
        else:
            assert False, "unknown user defined data_type %s" % data_type
        return schema

    def _generate_from_union(self, ctx, data_type):
        # type: (Context, StoneUnion) -> Schema
        own_properties = {}  # type: Dict[Text, Union[Schema, Reference]]
        description = data_type.doc + '\n' if data_type.doc else ''
        choices = []  # type: List[Text]
        for field in data_type.all_fields:
            description += '%s: %s\n' % (field.name, field.doc)
            choices.append(field.name)
            if is_void_type(field.data_type):
                continue
            property = self._generate_for_datatype(ctx, field.data_type)
            if isinstance(property, Schema):
                property.description = field.doc
            own_properties[field.name] = property
        own_properties['.tag'] = Schema(type='string', enum=choices, title='Choice of ' + data_type.name)
        schema = Schema(type='object', properties=own_properties, description=description)
        return schema

    def _generate_from_struct(self, ctx, data_type):
        # type: (Context, Struct) -> Schema
        own_properties = {}  # type: Dict[Text, Union[Schema, Reference]]
        description = data_type.doc + '\n' if data_type.doc else ''
        for field in data_type.all_fields:
            description += '%s: %s\n' % (field.name, field.doc)
            property = self._generate_for_datatype(ctx, field.data_type)
            if isinstance(property, Schema):
                property.description = field.doc
            own_properties[field.name] = property
        schema = Schema(type='object', properties=own_properties, description=description)
        return schema

    def _generate_primitive_type_schema(self, data_type):
        # type: (DataType) -> Schema
        field_type = self._generate_primitive_type_name(data_type)
        field_schema = Schema(type=field_type)
        return field_schema

    def _generate_primitive_type_name(self, data_type):
        # type: (DataType) -> Text
        if is_boolean_type(data_type):
            return 'boolean'
        if is_numeric_type(data_type):
            return 'number'
        if is_string_type(data_type):
            return 'string'
        if is_void_type(data_type):
            return 'null'
        if is_timestamp_type(data_type):
            return 'string'
        self.logger.warning('unknown primitive data_type %s' % format(data_type.name))
        return 'object'

    def _generate_reference_for_datatype(self, data_type):
        # type: (DataType) -> Reference
        return Reference('#/definitions/' + data_type.name)

    def _generate_reference_for_parameter(self, parameter_name):
        # type: (Text) -> Reference
        return Reference('#/parameters/' + parameter_name)
