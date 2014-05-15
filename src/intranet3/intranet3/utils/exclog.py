import pprint

def additional_message(request):
    """
    Hook for exclog.get_message http://pyramid-exclog.readthedocs.org/en/latest
    """
    msg = """
+++++++++++++++++++++++++++++++++++
{user}
+++++++++++++++++++++++++++++++++++
{request_env}
+++++++++++++++++++++++++++++++++++
"""
    return msg.format(
        user=request.user.email,
        request_env=pprint.pformat(request.environ),
    )