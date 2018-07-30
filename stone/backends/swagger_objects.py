from typing import Text, Optional, List, Dict, Union, Any


class Serializable(object):
    def __init__(self):
        self._renames = {'_renames': None}  # type: Dict[Text, Optional[Text]]

    def dict(self):
        d = {}  # type: Dict[Text, Any]
        for (k, v) in self.__dict__.items():
            if v is not None:
                if k in self._renames:
                    if self._renames[k] is not None:
                        d[self._renames[k]] = v
                else:
                    d[k] = v
        return d


class Swagger(Serializable):
    def __init__(
            self,
            swagger,            # type: Text
            info,               # type: Info
            paths,              # type: Paths
            host=None,          # type: Optional[Text]
            basePath=None,      # type: Optional[Text]
            schemes=None,       # type: Optional[List[Text]]
            consumes=None,      # type: Optional[List[Text]]
            produces=None,      # type: Optional[List[Text]]
            definitions=None,   # type: Optional[Definitions]
            security=None,      # type: Optional[SecurityRequirement]
            tags=None,          # type: Optional[Tag]
            externalDocs=None,  # type: Optional[ExternalDocumentation]
    ):
        super(Swagger, self).__init__()
        self.swagger = swagger
        self.info = info
        self.paths = paths
        self.host = host
        self.basePath = basePath
        self.schemes = schemes
        self.consumes = consumes
        self.produces = produces
        self.definitions = definitions
        self.security = security
        self.tags = tags
        self.externalDocs = externalDocs


class Info(Serializable):
    def __init__(
            self,
            title,                  # type: Text
            version,                # type: Text
            description=None,       # type: Optional[Text]
            termsOfService=None,    # type: Optional[Text]
            contact=None,           # type: Optional[Contact]
            license=None,           # type: Optional[License]
    ):
        super(Info, self).__init__()
        self.title = title
        self.version = version
        self.description = description
        self.termsOfService = termsOfService
        self.contact = contact
        self.license = license


class Contact(Serializable):
    def __init__(
            self,
            name=None,      # type: Optional[Text]
            url=None,       # type: Optional[Text]
            email=None,     # type: Optional[Text]
    ):
        super(Contact, self).__init__()
        self.name = name
        self.url = url
        self.email = email


class License(Serializable):
    def __init__(
            self,
            name=None,      # type: Optional[Text]
            url=None,       # type: Optional[Text]
    ):
        super(License, self).__init__()
        self.name = name
        self.url = url


class Paths(Serializable):
    def __init__(
            self,
            paths,      # type: Dict[Text, PathItem]
    ):
        super(Paths, self).__init__()
        self.__dict__.update(paths)

    def update(self, paths):
        # type: (Paths) -> None
        self.__dict__.update(paths.__dict__)


class PathItem(Serializable):
    def __init__(
            self,
            ref=None,           # type: Text
            get=None,           # type: Optional[Operation]
            put=None,           # type: Optional[Operation]
            post=None,          # type: Optional[Operation]
            delete=None,        # type: Optional[Operation]
            options=None,       # type: Optional[Operation]
            head=None,          # type: Optional[Operation]
            patch=None,         # type: Optional[Operation]
            parameters=None,    # type: List[Union[Parameter, Reference]]
    ):
        super(PathItem, self).__init__()
        self._renames['ref'] = '$ref'
        self.ref = ref
        self.get = get
        self.put = put
        self.post = post
        self.delete = delete
        self.options = options
        self.head = head
        self.patch = patch
        self.parameters = parameters


class Operation(Serializable):
    def __init__(
            self,
            responses,          # type: Responses
            tags=None,          # type: List[Text]
            summary=None,       # type: Optional[Text]
            description=None,   # type: Optional[Text]
            externalDocs=None,  # type: Optional[ExternalDocumentation]
            operationId=None,   # type: Optional[Text]
            consumes=None,      # type: Optional[List[Text]]
            produces=None,      # type: Optional[List[Text]]
            parameters=None,    # type: Optional[List[Union[Parameter, Reference]]]
            schemes=None,       # type: Optional[List[Text]]
            deprecated=None,    # type: Optional[bool]
            security=None,      # type: Optional[SecurityRequirement]
    ):
        super(Operation, self).__init__()
        self.responses = responses
        self.tags = tags
        self.summary = summary
        self.description = description
        self.externalDocs = externalDocs
        self.operationId = operationId
        self.consumes = consumes
        self.produces = produces
        self.parameters = parameters
        self.schemes = schemes
        self.deprecated = deprecated
        self.security = security


class ExternalDocumentation(Serializable):
    def __init__(
            self,
            url,                # type: Text
            description=None,   # type: Optional[Text]
    ):
        super(ExternalDocumentation, self).__init__()
        self.url = url
        self.description = description


class Parameter(Serializable):
    def __init__(
            self,
            name,                   # type: Text
            inParam,                # type: Text
            description=None,       # type: Optional[Text]
            required=None,          # type: Optional[bool]
            schema=None,            # type: Optional[Union[Schema, Reference]]
            type=None,              # type: Optional[Text]
    ):
        super(Parameter, self).__init__()
        self._renames['inParam'] = 'in'
        self.name = name
        self.inParam = inParam
        self.description = description
        self.required = required
        self.schema = schema
        self.type = type


class Responses(Serializable):
    def __init__(
            self,
            default=None,       # type: Optional[Union[Response, Reference]]
            statusCodes=None,   # type: Optional[Dict[Text, Union[Response, Reference]]]
    ):
        super(Responses, self).__init__()
        self.default = default
        if statusCodes is not None:
            self.__dict__.update(statusCodes)


class Response(Serializable):
    def __init__(
            self,
            description,        # type: Text
            schema=None,        # type: Optional[Union[Schema, Reference]]
            headers=None,       # type: Optional[Dict[Text, Union[Header, Reference]]]
            examples=None,      # type: Optional[Example]
    ):
        super(Response, self).__init__()
        self.description = description
        self.schema = schema
        self.headers = headers
        self.examples = examples


class Example(Serializable):
    def __init__(
            self,
            examples=None,  # type: Optional[Dict[Text, Any]]
    ):
        super(Example, self).__init__()
        self.__dict__.update(examples)


class Header(Serializable):
    def __init__(
            self,
            type,                   # type: Text
            description=None,       # type: Optional[Text]
    ):
        super(Header, self).__init__()
        self.type = type
        self.description = description


class Tag(Serializable):
    def __init__(
            self,
            name,                   # type: Text
            description=None,       # type: Optional[Text]
            externalDocs=None,      # type: Optional[ExternalDocumentation]
    ):
        super(Tag, self).__init__()
        self.name = name
        self.description = description
        self.externalDocs = externalDocs


class Reference(Serializable):
    def __init__(
            self,
            ref,    # type: Text
    ):
        super(Reference, self).__init__()
        self._renames['ref'] = '$ref'
        self.ref = ref


class Schema(Serializable):
    class Properties(Serializable):
        def __init__(
                self,
                properties,     # type: Dict[Text, Union[Schema, Reference]]
        ):
            super(Schema.Properties, self).__init__()
            self.__dict__.update(properties)


    def __init__(
            self,
            type=None,              # type: Optional[Text]
            title=None,             # type: Optional[Text]
            allOf=None,             # type: Optional[List[Union[Schema, Reference]]]
            items=None,             # type: Optional[Union[Schema, Reference]]
            properties=None,        # type: Optional[Dict[Text, Union[Schema, Reference]]]
            description=None,       # type: Optional[Text]
            format=None,            # type: Optional[Text]
            default=None,           # type: Any
            pattern=None,           # type: Optional[Text]
            required=None,          # type: Optional[bool]
            enum=None,              # type: Any
            discriminator=None,     # type: Optional[Text]
            readOnly=None,          # type: Optional[bool]
            xml=None,               # type: Optional[XML]
            externalDocs=None,      # type: Optional[ExternalDocumentation]
            example=None,           # type: Any
    ):
        super(Schema, self).__init__()
        self.type = type
        self.title = title
        self.allOf = allOf
        self.items = items
        self.properties = Schema.Properties(properties) if properties is not None else None
        self.description = description
        self.format = format
        self.default = default
        self.pattern = pattern
        self.required = required
        self.enum = enum
        self.discriminator = discriminator
        self.readOnly = readOnly
        self.xml = xml
        self.externalDocs = externalDocs
        self.example = example


class XML(Serializable):
    def __init__(
            self,
            name=None,          # type: Optional[Text]
            namespace=None,     # type: Optional[Text]
            prefix=None,        # type: Optional[Text]
            attribute=None,     # type: Optional[bool]
            wrapped=None,       # type: Optional[bool]
    ):
        super(XML, self).__init__()
        self.name = name
        self.namespace = namespace
        self.prefix = prefix
        self.attribute = attribute
        self.wrapped = wrapped


class Definitions(Serializable):
    def __init__(
            self,
            schemas,    # type: Dict[Text, Schema]
    ):
        super(Definitions, self).__init__()
        self.__dict__.update(schemas)


class SecurityScheme(Serializable):
    def __init__(
            self,
            type,                   # type: Text
            description=None,       # type: Optional[Text]
            name=None,              # type: Optional[Text]
            inParam=None,           # type: Optional[Text]
            flow=None,              # type: Optional[Text]
            authorizationUrl=None,  # type: Optional[Text]
            tokenUrl=None,          # type: Optional[Text]
            scopes=None,            # type: Optional[Scopes]
    ):
        super(SecurityScheme, self).__init__()
        self._renames['inParam'] = 'in'
        self.type = type
        self.description = description
        self.name = name
        self.inParam = inParam
        self.flow = flow
        self.authorizationUrl = authorizationUrl
        self.tokenUrl = tokenUrl
        self.scopes = scopes


class Scopes(Serializable):
    def __init__(
            self,
            scopes,     # type: Dict[Text, Text]
    ):
        super(Scopes, self).__init__()
        self.__dict__.update(scopes)


class SecurityRequirement(Serializable):
    def __init__(
            self,
            requirements,   # type: Dict[Text, List[Text]]
    ):
        super(SecurityRequirement, self).__init__()
        self.__dict__.update(requirements)
