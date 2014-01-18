# -*- coding: utf-8 -*-
import colander

class BoardSchema(colander.MappingSchema):
    board = colander.SchemaNode(colander.String())
    name = colander.SchemaNode(colander.String())
