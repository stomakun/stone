from distutils.version import StrictVersion

class Api(object):
    """
    A full description of an API's namespaces, data types, and operations.
    """
    def __init__(self, version):
        self.version = StrictVersion(version)
        self.namespaces = {}

    def ensure_namespace(self, name):
        """
        Only creates a namespace if it hasn't yet been defined.

        :param str name: Name of the namespace.

        :return ApiNamespace:
        """
        if name not in self.namespaces:
            self.namespaces[name] = ApiNamespace(name)
        return self.namespaces.get(name)

class ApiNamespace(object):
    def __init__(self, name):
        self.name = name
        self.operations = []
        self.data_types = []
    def add_operation(self, operation):
        self.operations.append(operation)
    def add_data_type(self, data_type):
        self.data_types.append(data_type)

class ApiOperation(object):
    """
    Represents an API endpoint.
    """

    def __init__(self,
                 name,
                 endpoint,
                 doc,
                 request_segmentation,
                 response_segmentation,
                 error_data_type):
        """
        :param str name: Friendly name of the endpoint.
        :param str endpoint: Request path.
        :param str doc: Description of the endpoint.
        :param Segmentation request_segmentation: The segmentation of the
            request.
        :param Segmentation segmentation: The segmentation of the response.
        :param DataType error_data_type: The data type that represents
            possible errors.
        """

        self.name = name
        self.endpoint = endpoint
        self.doc = doc
        self.request_segmentation = request_segmentation
        self.response_segmentation = response_segmentation
        self.error_data_type = error_data_type
