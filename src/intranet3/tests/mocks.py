class MockOAuth2FlowSampleData(object):
    def __init__(self):
        self.access_token = "1234567899"
        self.refresh_token = "1233456567"


def request_get(name, email):
    class MockRequestSampleData(object):
        def __init__(self, name, email):
            self.name = name
            self.email = email

        def json(self):
            return {
                'name': self.name,
                'email': self.email,
            }

    return MockRequestSampleData(name, email)


class MockApplicationConfig(object):

    def get_current_config(self, allow_empty=True):
        return self
