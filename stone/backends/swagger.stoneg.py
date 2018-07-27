import json

from typing import Dict, Text, Union, List, Optional, Tuple

from stone.ir import Api, ApiNamespace, ApiRoute, DataType, is_primitive_type, is_boolean_type, is_list_type, \
    is_numeric_type, is_string_type, is_void_type, is_timestamp_type, is_nullable_type, is_struct_type, \
    UserDefined, is_union_type, is_user_defined_type
from stone.backend import CodeBackend
from stone.backends.swagger_objects import Swagger, Info, Paths, PathItem, Operation, Schema, Reference, \
    Responses, Response, Parameter, Definitions

SWAGGER_VERSION = '2.0'
DEFAULT_SPEC_VERSION = '1.0.0'
DEFAULT_MEDIA_TYPE = 'application/json'


class SwaggerBackend(CodeBackend):

    def generate(self, api):
        # type: (Api) -> None
        for namespace in api.namespaces.values():
            if len(namespace.routes) > 0:
                with self.output_to_relative_path('{}.json'.format(namespace.name)):
                    swagger = self._generate_swagger(namespace)
                    self.emit_raw(json.dumps(swagger, default=lambda o: o.dict(), indent=2) + '\n')

    def _generate_swagger(self, namespace):
        # type: (ApiNamespace) -> Swagger
        info = self._generate_info(namespace)
        paths = self._generate_paths(namespace)
        definitions = self._generate_definitions(namespace)
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

    def _generate_paths(self, namespace):
        # type: (ApiNamespace) -> Paths
        paths = {
            '/' + route.name: self._generate_path_item(route)
            for route in namespace.routes
        }
        return Paths(paths)

    def _generate_path_item(self, route):
        # type: (ApiRoute) -> PathItem
        post = self._generate_operation(route)
        path_item = PathItem(post=post)
        return path_item

    def _generate_operation(self, route):
        # type: (ApiRoute) -> Operation
        summary, description = self._split_doc(route.doc) if route.doc else (None, None)
        parameters = self._generate_parameters(route)
        responses = self._generate_responses(route)
        operation_id = route.name.replace('/', '-')
        operation = Operation(responses, summary=summary, description=description, parameters=parameters, operationId=operation_id)
        return operation

    def _generate_parameters(self, route):
        # type: (ApiRoute) -> Optional[List[Parameter]]
        schema = self._generate_schema(route.arg_data_type)
        parameter = Parameter('body', 'body', schema=schema)
        # This is how I added the header for admins to assume users.
        # team_member_parameter = Parameter('Dropbox-API-Select-User', inParam='header', type='string')
        # return [parameter, team_member_parameter]
        return [parameter]

    def _generate_responses(self, route):
        # type: (ApiRoute) -> Responses
        description = ''
        default_schema = self._generate_schema(route.error_data_type)
        default_response = Response(description, schema=default_schema)
        ok_schema = self._generate_schema(route.result_data_type)
        ok_response = Response(description, schema=ok_schema)
        status_codes = {'200': ok_response}
        responses = Responses(default=default_response, statusCodes=status_codes)
        return responses

    def _generate_definitions(self, namespace):
        # type: (ApiNamespace) -> Definitions
        schemas = {}  # type: Dict[Text, Union[Schema, Reference]]
        for current in self._get_all_namespaces(namespace):
            schema = self._generate_schemas(current)
            schemas.update(schema)
        definitions = Definitions(schemas=schemas)
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

    def _generate_schemas(self, namespace):
        # type: (ApiNamespace) -> Dict[Text, Union[Schema, Reference]]
        schemas = {}  # type: Dict[Text, Union[Schema, Reference]]
        for data_type in namespace.linearize_data_types():
            name = data_type.name
            schema = self._generate_user_defined_schema(data_type)
            schemas[name] = schema
        return schemas

    def _generate_user_defined_schema(self, data_type):
        # type: (UserDefined) -> Schema
        if is_struct_type(data_type):
            schema = self._generate_from_struct(data_type)
        elif is_union_type(data_type):
            schema = self._generate_from_union(data_type)
        else:
            self.logger.warning("unknown user defined data_type %s" % data_type)
            schema = None
        return schema

    def _generate_from_union(self, data_type):
        # type: (UserDefined) -> Schema
        description = data_type.doc
        own_properties = {}  # type: Dict[Text, Union[Schema, Reference]]
        choices = []  # type: List[Text]
        for field in data_type.all_fields:
            field_name = field.name
            choices.append(field_name)
            if is_void_type(field.data_type):
                continue
            field_description = field.doc
            property = self._generate_schema(field.data_type, description=field_description)
            own_properties[field_name] = property
        own_properties['.tag'] = Schema(type='string', enum=choices, title='Union ' + data_type.name)
        schema = Schema(type='object', properties=own_properties, description=description)
        return schema

    def _generate_from_struct(self, data_type):
        # type: (UserDefined) -> Schema
        description = data_type.doc
        own_properties = {}  # type: Dict[Text, Union[Schema, Reference]]
        for field in data_type.all_fields:
            field_name = field.name
            field_description = field.doc
            property = self._generate_schema(field.data_type, description=field_description)
            own_properties[field_name] = property
        schema = Schema(type='object', properties=own_properties, description=description)
        # if data_type.parent_type is not None:
        #     all_of = [self._generate_reference(data_type.parent_type), schema]
        #     schema = Schema(allOf=all_of, description=description)
        return schema

    def _generate_schema(self, data_type, description=None, title=None):
        # type: (DataType, Optional[Text], Optional[Text]) -> Union[Schema, Reference]
        schema = None   # type: Optional[Union[Schema, Reference]]
        if is_primitive_type(data_type):
            schema = self._generate_primitive_type_schema(data_type)
            schema.description = description
            schema.title = title
        elif is_list_type(data_type):
            schema = Schema(type='array', items=self._generate_schema(data_type.data_type))
            schema.description = description
            schema.title = title
        elif is_nullable_type(data_type):
            schema = self._generate_schema(data_type.data_type, description, title)
        elif is_user_defined_type(data_type):
            schema = self._generate_reference(data_type)
        else:
            self.logger.warning("unknown field data_type %s" % data_type)
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
        lines = doc.splitlines()
        summary = lines[0] if len(lines) > 0 else ''
        summary = summary.rstrip(' ').rstrip('.')
        description = '\n'.join(lines[1:]) if len(lines) > 1 else ''
        return summary, description
