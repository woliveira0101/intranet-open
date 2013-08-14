# coding: utf-8
from colander import MappingSchema, SchemaNode, Boolean, Float, Integer, \
    String, Range, Invalid


class TimeObject(object):
    """
        Time format: float `1.2` or `HH:MM`
    """
    def deserialize(self, node, cstruct):
        if not isinstance(cstruct, float) and not isinstance(cstruct, basestring):
            raise Invalid(node, "Invalid format: float or HH:MM")

        if isinstance(cstruct, float):
            data = cstruct

        if isinstance(cstruct, basestring) and cstruct.count(':'):
            try:
                h, min = [int(i) for i in cstruct.split(':')]
            except ValueError:
                raise Invalid(node, "Time must be a number in format HH:MM")
            else:
                if h < 0 or min < 0:
                    raise Invalid(node, "Hours and minutes must be a positive number")
                
                if h >= 24:
                    raise Invalid("Hours can not be greater or equal than 24")
                
                if min >= 60:
                    raise Invalid("Minutes can not be greater or equal than 60")

                data = h + (float(min) / 60.0)

        if not isinstance(cstruct, float): # "3.5"
            data = cstruct.replace(',', '.')

        if not isinstance(data, float):
            data = data.replace(',', '.')
            try:
                data = float(data)
            except ValueError:
                raise Invalid(node, "Time must be a float or HH:MM") 

        return data


class TicketObject(object):
    def deserialize(self, node, cstruct):
        if isinstance(cstruct, basestring) or isinstance(cstruct, int):
            return cstruct  

        raise Invalid(node, "Ticket should be String or Int")  


class AddEntrySchema(MappingSchema):
    user_id = SchemaNode(Integer())
    project_id = SchemaNode(Integer())
    ticket_id = SchemaNode(TicketObject())
    time = SchemaNode(TimeObject(), validator=Range(0.0, 24.00))
    description = SchemaNode(String())
    timer = SchemaNode(Boolean())
    add_to_harvest = SchemaNode(Boolean())


class EditEntrySchema(MappingSchema):
    project_id = SchemaNode(Integer())
    ticket_id = SchemaNode(TicketObject())
    time = SchemaNode(TimeObject(), validator=Range(0.0, 24.00))
    description = SchemaNode(String())