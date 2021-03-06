# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 CERN.
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Community schema."""

from marshmallow import Schema, fields


class CommunitiesSchema(Schema):
    """Community schema."""

    ids = fields.List(fields.String())
    default = fields.String()
