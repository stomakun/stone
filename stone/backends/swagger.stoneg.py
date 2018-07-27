import json

from typing import Dict, Text, Union, List, Optional, Tuple

from stone.ir import Api, ApiNamespace, ApiRoute, DataType, is_primitive_type, is_boolean_type, is_list_type, \
    is_numeric_type, is_string_type, is_void_type, is_timestamp_type, is_nullable_type, is_struct_type, \
    UserDefined, is_union_type, is_user_defined_type, Struct, Union as StoneUnion
from stone.backend import CodeBackend
from stone.backends.swagger_objects import Swagger, Info, Paths, PathItem, Operation, Schema, Reference, \
    Responses, Response, Parameter, Definitions

SWAGGER_VERSION = '2.0'
DEFAULT_SPEC_VERSION = '1.0.0'
DEFAULT_MEDIA_TYPE = 'application/json'


class Context(object):

    def __init__(self):
        self.schemas = {}   # type: Dict[Text, Schema]


class SwaggerBackend(CodeBackend):

    def generate(self, api):
        # type: (Api) -> None
        for namespace in api.namespaces.values():
            if len(namespace.routes) > 0:
                with self.output_to_relative_path('{}.json'.format(namespace.name)):
                    swagger = self._generate_swagger(Context(), namespace)
                    self.emit_raw(json.dumps(swagger, default=lambda o: o.dict(), indent=2) + '\n')

    def _generate_swagger(self, ctx, namespace):
        # type: (Context, ApiNamespace) -> Swagger
        info = self._generate_info(namespace)
        paths = self._generate_paths(ctx, namespace)
        definitions = self._generate_definitions(ctx)
        mimes = [DEFAULT_MEDIA_TYPE]
        host = 'api.dropboxapi.com'
        base_path = '/2/' + namespace.name
        swagger = Swagger(SWAGGER_VERSION, info, paths, consumes=mimes, produces=mimes, definitions=definitions, host=host, basePath=base_path)
        return swagger

    def _generate_info(self, namespace):
        # type: (ApiNamespace) -> Info
        title = namespace.name
        description = namespace.doc
        info = Info(title, DEFAULT_SPEC_VERSION, description=description)
        return info

    def _generate_paths(self, ctx, namespace):
        # type: (Context, ApiNamespace) -> Paths
        paths = {
            '/' + route.name: self._generate_path_item(ctx, route)
            for route in namespace.routes
        }
        return Paths(paths)

    def _generate_path_item(self, ctx, route):
        # type: (Context, ApiRoute) -> PathItem
        post = self._generate_operation(ctx, route)
        path_item = PathItem(post=post)
        return path_item

    def _generate_operation(self, ctx, route):
        # type: (Context, ApiRoute) -> Operation
        summary, description = self._split_doc(route.doc) if route.doc else ('', None)
        summary = route.name + ': ' + summary
        parameters = self._generate_parameters(ctx, route)
        responses = self._generate_responses(ctx, route)
        operation_id = route.name.replace('/', '-')
        operation = Operation(responses, summary=summary, description=description, parameters=parameters, operationId=operation_id)
        return operation

    def _generate_parameters(self, ctx, route):
        # type: (Context, ApiRoute) -> Optional[List[Parameter]]
        schema = self._generate_for_datatype(ctx, route.arg_data_type)
        parameter = Parameter('body', 'body', schema=schema)
        # This is how I added the header for admins to assume users.
        # team_member_parameter = Parameter('Dropbox-API-Select-User', inParam='header', type='string')
        # return [parameter, team_member_parameter]
        return [parameter]

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
            schema = self._generate_reference(data_type)
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

    def _get_all_namespaces(self, namespace):
        # type: (ApiNamespace) -> List[ApiNamespace]
        namespaces = {namespace.name: namespace}
        stack = [namespace]
        while len(stack) > 0:
            current = stack.pop()
            for imported in current.get_imported_namespaces():
                if imported.name not in namespaces:
                    namespaces[imported.name] = imported
                    stack.append(imported)
        return list(namespaces.values())

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
        description = data_type.doc or ''
        choices = []  # type: List[Text]
        for field in data_type.all_fields:
            description += '\n%s: %s' % (field.name, field.doc)
            choices.append(field.name)
            if is_void_type(field.data_type):
                continue
            property = self._generate_for_datatype(ctx, field.data_type)
            if isinstance(property, Schema):
                property.description = field.doc
            own_properties[field.name] = property
        own_properties['.tag'] = Schema(type='string', enum=choices, title='Union type of ' + data_type.name)
        schema = Schema(type='object', properties=own_properties, description=description)
        return schema

    def _generate_from_struct(self, ctx, data_type):
        # type: (Context, Struct) -> Schema
        own_properties = {}  # type: Dict[Text, Union[Schema, Reference]]
        description = data_type.doc or ''
        for field in data_type.all_fields:
            description += '\n%s: %s' % (field.name, field.doc)
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

    def _generate_reference(self, data_type):
        # type: (DataType) -> Reference
        return Reference('#/definitions/' + data_type.name)

    def _split_doc(self, doc):
        # type: (Text) -> Tuple[Text, Text]
        pos = doc.find('. ')
        if pos == -1:
            pos = doc.find('.\n')
        if pos == -1:
            return doc, ''
        return doc[:pos], doc[pos+2:]
